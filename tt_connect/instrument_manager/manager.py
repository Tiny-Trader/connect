from __future__ import annotations
from datetime import date
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import aiosqlite
from tt_connect.enums import Exchange, OnStale, OptionType
from tt_connect.exceptions import TTConnectError, InstrumentManagerError
from tt_connect.instrument_manager.db import get_connection, init_schema, truncate_all
from tt_connect.instruments import Equity, Future, Instrument, Option

logger = logging.getLogger(__name__)

class ParsedInstrumentsLike(Protocol):
    indices: list[Any]
    equities: list[Any]
    futures: list[Any]
    options: list[Any]


class InstrumentManager:
    """Maintains the local instrument master and staleness lifecycle."""

    def __init__(self, broker_id: str, on_stale: OnStale = OnStale.FAIL):
        self._broker_id = broker_id
        self._on_stale = on_stale
        self._conn: aiosqlite.Connection | None = None

    def _conn_or_raise(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise InstrumentManagerError("InstrumentManager not initialized. Call init() first.")
        return self._conn

    async def init(self, fetch_fn: Callable[[], Awaitable[ParsedInstrumentsLike]]) -> None:
        """Open DB, initialize schema, and ensure data freshness."""
        self._conn = await get_connection(self._broker_id)
        await init_schema(self._conn_or_raise())
        await self.ensure_fresh(fetch_fn)

    async def ensure_fresh(self, fetch_fn: Callable[[], Awaitable[ParsedInstrumentsLike]]) -> None:
        """Refresh stale data; optionally fall back to cached data on failure.

        Behavior depends on `on_stale`:
        - `FAIL`: raise refresh errors immediately.
        - `WARN`: use stale cache only if at least one instrument exists.
        """
        if await self._is_stale():
            try:
                await self.refresh(fetch_fn)
            except Exception as e:
                logger.warning(
                    f"Instrument refresh failed: {e}",
                    extra={"event": "instruments.refresh.failed", "broker": self._broker_id},
                )
                if self._on_stale == OnStale.FAIL:
                    raise
                # WARN mode: only fall back to stale data if data actually exists.
                # On a first run with no DB, there's nothing to serve — fail clearly.
                if not await self._has_any_data():
                    raise TTConnectError(
                        "Instrument data download failed and no cached data exists. "
                        "Check your network connection and try again."
                    ) from e
                logger.warning(
                    f"Instrument refresh failed, using stale data: {e}",
                    extra={"event": "instruments.stale_fallback", "broker": self._broker_id},
                )

    async def refresh(self, fetch_fn: Callable[[], Awaitable[ParsedInstrumentsLike]]) -> None:
        """Fetch broker instruments and atomically rebuild local tables."""
        logger.info(
            f"Refreshing instruments for {self._broker_id}",
            extra={"event": "instruments.refresh.start", "broker": self._broker_id},
        )
        t0 = time.monotonic()
        parsed: ParsedInstrumentsLike = await fetch_fn()
        await truncate_all(self._conn_or_raise())
        await self._insert(parsed)
        await self._set_last_updated()
        logger.info(
            "Instrument refresh complete",
            extra={
                "event": "instruments.refresh.end",
                "broker": self._broker_id,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
            },
        )

    async def _insert(self, parsed: ParsedInstrumentsLike) -> None:
        """Insert parsed instruments in dependency-safe order."""
        # Chunk 1: indices — must exist before futures/options reference them
        await self._insert_indices(parsed.indices)

        # Chunk 2: equities
        await self._insert_equities(parsed.equities)

        # Chunk 3: futures — underlying_id resolved from lookup built after chunks 1+2
        lookup = await self._build_underlying_lookup()
        await self._insert_futures(parsed.futures, lookup)

        # Chunk 4: options — same lookup, already built
        await self._insert_options(parsed.options, lookup)

        await self._conn_or_raise().commit()

    async def _insert_indices(self, indices: list[Any]) -> None:
        if not indices:
            return

        logger.info(f"Inserting {len(indices)} indices")

        for idx in indices:
            # 1. Base instrument record
            cursor = await self._conn_or_raise().execute(
                """
                INSERT INTO instruments (exchange, symbol, segment, name, lot_size, tick_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (idx.exchange, idx.symbol, idx.segment, idx.name, idx.lot_size, idx.tick_size),
            )
            instrument_id = cursor.lastrowid

            # 2. Equities sub-table (indices have no ISIN)
            await self._conn_or_raise().execute(
                "INSERT INTO equities (instrument_id, isin) VALUES (?, NULL)",
                (instrument_id,),
            )

            # 3. Broker token
            await self._conn_or_raise().execute(
                """
                INSERT INTO broker_tokens (instrument_id, broker_id, token, broker_symbol)
                VALUES (?, ?, ?, ?)
                """,
                (instrument_id, self._broker_id, idx.broker_token, idx.broker_symbol),
            )

    async def _insert_equities(self, equities: list[Any]) -> None:
        if not equities:
            return

        logger.info(f"Inserting {len(equities)} equities")

        for eq in equities:
            # 1. Base instrument record
            cursor = await self._conn_or_raise().execute(
                """
                INSERT INTO instruments (exchange, symbol, segment, name, lot_size, tick_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (eq.exchange, eq.symbol, eq.segment, eq.name, eq.lot_size, eq.tick_size),
            )
            instrument_id = cursor.lastrowid

            # 2. Equities sub-table (Zerodha CSV has no ISIN)
            await self._conn_or_raise().execute(
                "INSERT INTO equities (instrument_id, isin) VALUES (?, NULL)",
                (instrument_id,),
            )

            # 3. Broker token
            await self._conn_or_raise().execute(
                """
                INSERT INTO broker_tokens (instrument_id, broker_id, token, broker_symbol)
                VALUES (?, ?, ?, ?)
                """,
                (instrument_id, self._broker_id, eq.broker_token, eq.broker_symbol),
            )

    async def _build_underlying_lookup(self) -> dict[tuple[str, str], int]:
        """
        Build a {(exchange, symbol) → instrument_id} dict from all rows currently
        in the instruments table. Called after indices + equities are inserted so
        futures can resolve their underlying_id without per-row SELECT queries.
        """
        async with self._conn_or_raise().execute(
            "SELECT id, exchange, symbol FROM instruments"
        ) as cur:
            rows = await cur.fetchall()
        return {(row[1], row[2]): row[0] for row in rows}

    async def _insert_futures(self, futures: list[Any], lookup: dict[tuple[str, str], int]) -> None:
        if not futures:
            return

        logger.info(f"Inserting {len(futures)} futures")
        skipped = 0

        for fut in futures:
            underlying_id = lookup.get((fut.underlying_exchange, fut.symbol))
            if underlying_id is None:
                logger.warning(
                    f"Skipping {fut.broker_symbol}: underlying "
                    f"({fut.underlying_exchange}, {fut.symbol}) not in DB"
                )
                skipped += 1
                continue

            # 1. Base instrument record
            cursor = await self._conn_or_raise().execute(
                """
                INSERT INTO instruments (exchange, symbol, segment, name, lot_size, tick_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (fut.exchange, fut.symbol, fut.segment, None, fut.lot_size, fut.tick_size),
            )
            instrument_id = cursor.lastrowid

            # 2. Futures sub-table
            await self._conn_or_raise().execute(
                "INSERT INTO futures (instrument_id, underlying_id, expiry) VALUES (?, ?, ?)",
                (instrument_id, underlying_id, fut.expiry.isoformat()),
            )

            # 3. Broker token
            await self._conn_or_raise().execute(
                """
                INSERT INTO broker_tokens (instrument_id, broker_id, token, broker_symbol)
                VALUES (?, ?, ?, ?)
                """,
                (instrument_id, self._broker_id, fut.broker_token, fut.broker_symbol),
            )

        if skipped:
            logger.warning(f"Skipped {skipped} futures due to unresolved underlyings")

    async def _insert_options(self, options: list[Any], lookup: dict[tuple[str, str], int]) -> None:
        if not options:
            return

        logger.info(f"Inserting {len(options)} options")
        skipped = 0

        for opt in options:
            underlying_id = lookup.get((opt.underlying_exchange, opt.symbol))
            if underlying_id is None:
                logger.warning(
                    f"Skipping {opt.broker_symbol}: underlying "
                    f"({opt.underlying_exchange}, {opt.symbol}) not in DB"
                )
                skipped += 1
                continue

            # 1. Base instrument record
            cursor = await self._conn_or_raise().execute(
                """
                INSERT INTO instruments (exchange, symbol, segment, name, lot_size, tick_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (opt.exchange, opt.symbol, opt.segment, None, opt.lot_size, opt.tick_size),
            )
            instrument_id = cursor.lastrowid

            # 2. Options sub-table
            await self._conn_or_raise().execute(
                """
                INSERT INTO options (instrument_id, underlying_id, expiry, strike, option_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (instrument_id, underlying_id, opt.expiry.isoformat(), opt.strike, opt.option_type),
            )

            # 3. Broker token
            await self._conn_or_raise().execute(
                """
                INSERT INTO broker_tokens (instrument_id, broker_id, token, broker_symbol)
                VALUES (?, ?, ?, ?)
                """,
                (instrument_id, self._broker_id, opt.broker_token, opt.broker_symbol),
            )

        if skipped:
            logger.warning(f"Skipped {skipped} options due to unresolved underlyings")

    async def _has_any_data(self) -> bool:
        """Return True if the local instrument DB already has at least one row."""
        async with self._conn_or_raise().execute("SELECT COUNT(*) FROM instruments") as cur:
            row = await cur.fetchone()
        return row is not None and row[0] > 0

    async def _is_stale(self) -> bool:
        """Return True when `_meta.last_updated` is missing or not today."""
        async with self._conn_or_raise().execute(
            "SELECT value FROM _meta WHERE key = 'last_updated'"
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return True
        return str(row[0]) != date.today().isoformat()

    async def _set_last_updated(self) -> None:
        """Persist today's date as the successful refresh marker."""
        await self._conn_or_raise().execute(
            "INSERT OR REPLACE INTO _meta(key, value) VALUES ('last_updated', ?)",
            (date.today().isoformat(),),
        )
        await self._conn_or_raise().commit()

    # ---------------------------------------------------------------------------
    # Instrument master queries
    # ---------------------------------------------------------------------------

    async def get_futures(self, underlying: Instrument) -> list[Future]:
        """Return all active futures for an underlying instrument, sorted by expiry."""
        query = """
            SELECT u.exchange, u.symbol, f.expiry
            FROM instruments fut
            JOIN futures f     ON f.instrument_id = fut.id
            JOIN instruments u ON u.id = f.underlying_id
            WHERE u.exchange = ? AND u.symbol = ?
            ORDER BY f.expiry ASC
        """
        async with self._conn_or_raise().execute(
            query, (str(underlying.exchange), underlying.symbol)
        ) as cur:
            rows = await cur.fetchall()
        return [
            Future(
                exchange=Exchange(row[0]),
                symbol=row[1],
                expiry=date.fromisoformat(row[2]),
            )
            for row in rows
        ]

    async def get_options(
        self,
        underlying: Instrument,
        expiry: date | None = None,
    ) -> list[Option]:
        """Return options for an underlying, optionally filtered by expiry.

        Results are sorted by expiry → strike → option_type (CE before PE).
        """
        if expiry is not None:
            query = """
                SELECT u.exchange, u.symbol, o.expiry, o.strike, o.option_type
                FROM instruments opt
                JOIN options o     ON o.instrument_id = opt.id
                JOIN instruments u ON u.id = o.underlying_id
                WHERE u.exchange = ? AND u.symbol = ? AND o.expiry = ?
                ORDER BY o.expiry ASC, o.strike ASC, o.option_type ASC
            """
            params: tuple[Any, ...] = (str(underlying.exchange), underlying.symbol, expiry.isoformat())
        else:
            query = """
                SELECT u.exchange, u.symbol, o.expiry, o.strike, o.option_type
                FROM instruments opt
                JOIN options o     ON o.instrument_id = opt.id
                JOIN instruments u ON u.id = o.underlying_id
                WHERE u.exchange = ? AND u.symbol = ?
                ORDER BY o.expiry ASC, o.strike ASC, o.option_type ASC
            """
            params = (str(underlying.exchange), underlying.symbol)
        async with self._conn_or_raise().execute(query, params) as cur:
            rows = await cur.fetchall()
        return [
            Option(
                exchange=Exchange(row[0]),
                symbol=row[1],
                expiry=date.fromisoformat(row[2]),
                strike=float(row[3]),
                option_type=OptionType(row[4]),
            )
            for row in rows
        ]

    async def get_expiries(self, underlying: Instrument) -> list[date]:
        """Return all distinct expiry dates for an underlying across futures and options."""
        query = """
            SELECT DISTINCT expiry FROM (
                SELECT f.expiry FROM futures f
                JOIN instruments u ON u.id = f.underlying_id
                WHERE u.exchange = ? AND u.symbol = ?
                UNION
                SELECT o.expiry FROM options o
                JOIN instruments u ON u.id = o.underlying_id
                WHERE u.exchange = ? AND u.symbol = ?
            )
            ORDER BY expiry ASC
        """
        async with self._conn_or_raise().execute(
            query,
            (str(underlying.exchange), underlying.symbol,
             str(underlying.exchange), underlying.symbol),
        ) as cur:
            rows = await cur.fetchall()
        return [date.fromisoformat(row[0]) for row in rows]

    async def search_instruments(
        self,
        query: str,
        exchange: str | None = None,
    ) -> list[Equity]:
        """Search underlyings (equities + indices) by symbol substring.

        Matching is case-insensitive. Results are sorted by exchange then symbol
        and capped at 50 entries.
        """
        pattern = f"%{query.upper()}%"
        if exchange is not None:
            sql = """
                SELECT i.exchange, i.symbol
                FROM instruments i
                JOIN equities e ON e.instrument_id = i.id
                WHERE UPPER(i.symbol) LIKE ? AND i.exchange = ?
                ORDER BY i.exchange, i.symbol
                LIMIT 50
            """
            params: tuple[Any, ...] = (pattern, exchange)
        else:
            sql = """
                SELECT i.exchange, i.symbol
                FROM instruments i
                JOIN equities e ON e.instrument_id = i.id
                WHERE UPPER(i.symbol) LIKE ?
                ORDER BY i.exchange, i.symbol
                LIMIT 50
            """
            params = (pattern,)
        async with self._conn_or_raise().execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [Equity(exchange=Exchange(row[0]), symbol=row[1]) for row in rows]

    @property
    def connection(self) -> aiosqlite.Connection:
        """Expose initialized DB connection to resolver/client layers."""
        if not self._conn:
            raise InstrumentManagerError("InstrumentManager not initialized. Call init() first.")
        return self._conn
