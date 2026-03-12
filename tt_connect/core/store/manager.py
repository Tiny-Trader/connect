"""SQLite-backed instrument manager — refresh and staleness lifecycle.

This module owns the full instrument data lifecycle:

1. **Download** — calls the broker adapter's ``fetch_instruments()`` via a
   callback, receiving a ``ParsedInstrumentsLike`` container.
2. **Store** — inserts indices → equities → futures → options into SQLite
   in dependency-safe order (parent rows before FK children).
3. **Staleness** — tracks ``last_updated`` in a ``_meta`` table; data older
   than today is considered stale and triggers a fresh download.
The manager never imports broker code directly. It accepts any object
satisfying :class:`ParsedInstrumentsLike` via structural typing.
"""

from __future__ import annotations
from datetime import date
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import aiosqlite
from tt_connect.core.models.enums import OnStale
from tt_connect.core.exceptions import InstrumentManagerError, InstrumentStoreNotInitializedError, TTConnectError
from tt_connect.core.store.queries import InstrumentQueries
from tt_connect.core.store.schema import get_connection, init_schema

logger = logging.getLogger(__name__)

class ParsedInstrumentsLike(Protocol):
    """Structural contract for broker-parsed instrument data.

    Each broker defines its own ``ParsedInstruments`` dataclass in
    ``brokers/<name>/parser.py`` with concrete typed fields. This Protocol
    lets the core accept any of them without importing broker code —
    preserving the strict ``core → brokers`` dependency direction.

    Any object with these four list attributes satisfies the Protocol
    via duck typing (no explicit inheritance required). Each list item
    is expected to carry at least ``.exchange``, ``.symbol``,
    ``.broker_symbol``, and ``.broker_token`` attributes.
    """

    indices: list[Any]    #: Index instruments (must be inserted first — FKs depend on them)
    equities: list[Any]   #: Cash equities (NSE/BSE EQ segment)
    futures: list[Any]    #: Futures contracts (require ``underlying_exchange`` for FK resolution)
    options: list[Any]    #: Options contracts (require ``underlying_exchange``, ``strike``, ``option_type``)


class InstrumentManager:
    """Maintains the local SQLite instrument master and staleness lifecycle.

    Responsibilities:
        - Open a per-broker SQLite database under ``_cache/``.
        - Check whether cached data is stale (not updated today).
        - Download and atomically replace instrument data when stale.

    The ``on_stale`` policy controls behavior when a refresh fails:
        - ``OnStale.FAIL`` — raise immediately (default, safest for prod).
        - ``OnStale.WARN`` — fall back to yesterday's cache if it exists,
          log a warning, and continue.
    """

    def __init__(self, broker_id: str, on_stale: OnStale = OnStale.FAIL):
        """Create an instrument manager for a specific broker.

        Args:
            broker_id: Identifier used for the database filename and
                broker_tokens table filtering (e.g. ``"zerodha"``).
            on_stale: Policy when instrument refresh fails — see class docstring.
        """
        self._broker_id = broker_id
        self._on_stale = on_stale
        self._conn: aiosqlite.Connection | None = None
        self._queries = InstrumentQueries(None)

    def _conn_or_raise(self) -> aiosqlite.Connection:
        """Return the active DB connection, or raise if ``init()`` was not called."""
        if self._conn is None:
            raise InstrumentManagerError("InstrumentManager not initialized. Call init() first.")
        return self._conn

    async def init(self, fetch_fn: Callable[[], Awaitable[ParsedInstrumentsLike]]) -> None:
        """Open DB, initialize schema, and ensure data freshness."""
        self._conn = await get_connection(self._broker_id)
        try:
            await init_schema(self._conn_or_raise())
            await self.ensure_fresh(fetch_fn)
        except Exception:
            await self._cleanup_failed_init()
            raise
        self._queries.bind(self._conn)

    async def open_existing(self) -> None:
        """Open an existing local DB for read-only query use."""
        self._conn = await get_connection(self._broker_id)
        try:
            await init_schema(self._conn_or_raise())
            if not await self._has_any_data():
                raise InstrumentStoreNotInitializedError(
                    "Instrument DB not initialized. Initialize TTConnect or AsyncTTConnect first "
                    "to seed or refresh instruments before using InstrumentStore."
                )
        except Exception:
            await self._cleanup_failed_init()
            raise
        self._queries.bind(self._conn)

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
            f"[{self._broker_id}] Downloading instrument master",
            extra={"event": "instruments.refresh.start", "broker": self._broker_id},
        )
        t0 = time.monotonic()
        parsed: ParsedInstrumentsLike = await fetch_fn()
        conn = self._conn_or_raise()
        try:
            await conn.execute("BEGIN")
            for table in ("broker_tokens", "equities", "futures", "options", "instruments"):
                await conn.execute(f"DELETE FROM {table}")
            await conn.execute("DELETE FROM _meta WHERE key = 'last_updated'")
            counts = await self._insert(parsed)
            await self._set_last_updated()
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            f"[{self._broker_id}] Instruments ready"
            f" — {counts['indices']} indices · {counts['equities']} equities"
            f" · {counts['futures']} futures · {counts['options']} options"
            f" ({elapsed_ms}ms)",
            extra={
                "event": "instruments.refresh.end",
                "broker": self._broker_id,
                "elapsed_ms": elapsed_ms,
                **counts,
            },
        )

    async def _insert(self, parsed: ParsedInstrumentsLike) -> dict[str, int]:
        """Insert parsed instruments in dependency-safe order.

        Returns a count dict with keys: indices, equities, futures, options.
        """
        # Chunk 1: indices — must exist before futures/options reference them
        n_idx = await self._insert_indices(parsed.indices)

        # Chunk 2: equities
        n_eq = await self._insert_equities(parsed.equities)

        # Chunk 3: futures — underlying_id resolved from lookup built after chunks 1+2
        lookup = await self._build_underlying_lookup()
        n_fut, missing_fut = await self._insert_futures(parsed.futures, lookup)

        # Chunk 4: options — same lookup, already built
        n_opt, missing_opt = await self._insert_options(parsed.options, lookup)
        # Emit grouped DEBUG summaries for skipped instruments (expected for some
        # brokers where certain BSE underlyings are absent from the instrument dump).
        if missing_fut:
            skipped = len(parsed.futures) - n_fut
            logger.debug(
                f"[{self._broker_id}] Skipped {skipped} futures"
                f" — {len(missing_fut)} underlyings not in DB:"
                f" {', '.join(sorted(missing_fut))}",
                extra={
                    "event": "instruments.skipped.futures",
                    "broker": self._broker_id,
                    "count": skipped,
                    "underlyings": sorted(missing_fut),
                },
            )
        if missing_opt:
            skipped = len(parsed.options) - n_opt
            logger.debug(
                f"[{self._broker_id}] Skipped {skipped} options"
                f" — {len(missing_opt)} underlyings not in DB:"
                f" {', '.join(sorted(missing_opt))}",
                extra={
                    "event": "instruments.skipped.options",
                    "broker": self._broker_id,
                    "count": skipped,
                    "underlyings": sorted(missing_opt),
                },
            )

        return {"indices": n_idx, "equities": n_eq, "futures": n_fut, "options": n_opt}

    async def _insert_indices(self, indices: list[Any]) -> int:
        """Insert index rows into ``instruments`` + ``equities`` + ``broker_tokens``.

        Indices are inserted first because futures and options hold foreign keys
        to their underlying, which may be an index (e.g. NIFTY, BANKNIFTY).
        Returns the count of inserted rows.
        """
        if not indices:
            return 0

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

        return len(indices)

    async def _insert_equities(self, equities: list[Any]) -> int:
        """Insert cash equity rows into ``instruments`` + ``equities`` + ``broker_tokens``.

        Inserted after indices so that the underlying lookup (used by futures
        and options) contains both indices and stocks.
        Returns the count of inserted rows.
        """
        if not equities:
            return 0

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

        return len(equities)

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

    async def _insert_futures(
        self, futures: list[Any], lookup: dict[tuple[str, str], int]
    ) -> tuple[int, set[str]]:
        """Insert futures rows, resolving ``underlying_id`` from the lookup.

        Each future item must carry ``underlying_exchange`` (e.g. ``"NSE"``)
        so the FK to the parent index/equity can be resolved. Rows whose
        underlying is missing from the DB are silently collected and returned
        for a single grouped DEBUG log by the caller.

        Returns:
            (inserted_count, missing_underlyings) where missing_underlyings is
            a set of ``"EXCHANGE:SYMBOL"`` strings for skipped rows.
        """
        if not futures:
            return 0, set()

        inserted = 0
        missing: set[str] = set()

        for fut in futures:
            underlying_id = lookup.get((fut.underlying_exchange, fut.symbol))
            if underlying_id is None:
                missing.add(f"{fut.underlying_exchange}:{fut.symbol}")
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
            inserted += 1

        return inserted, missing

    async def _insert_options(
        self, options: list[Any], lookup: dict[tuple[str, str], int]
    ) -> tuple[int, set[str]]:
        """Insert options rows, resolving ``underlying_id`` from the lookup.

        Same resolution logic as ``_insert_futures``. Each option item must
        additionally carry ``strike`` and ``option_type`` (``"CE"`` / ``"PE"``).

        Returns:
            (inserted_count, missing_underlyings) where missing_underlyings is
            a set of ``"EXCHANGE:SYMBOL"`` strings for skipped rows.
        """
        if not options:
            return 0, set()

        inserted = 0
        missing: set[str] = set()

        for opt in options:
            underlying_id = lookup.get((opt.underlying_exchange, opt.symbol))
            if underlying_id is None:
                missing.add(f"{opt.underlying_exchange}:{opt.symbol}")
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
            inserted += 1

        return inserted, missing

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

    async def _cleanup_failed_init(self) -> None:
        """Close and unbind the connection after an init/open failure."""
        self._queries.bind(None)
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def queries(self) -> InstrumentQueries:
        """Expose the bound read-only query layer."""
        return self._queries

    @property
    def connection(self) -> aiosqlite.Connection:
        """Expose initialized DB connection to resolver/client layers."""
        if not self._conn:
            raise InstrumentManagerError("InstrumentManager not initialized. Call init() first.")
        return self._conn
