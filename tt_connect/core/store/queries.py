"""Read-only discovery queries over the local SQLite instrument cache.

This module owns the *catalog-style* lookup surface for instruments that have
already been downloaded and stored locally. Unlike ``manager.py``, it does not
perform refreshes, staleness checks, or writes; and unlike ``resolver.py``, it
does not translate canonical instruments into broker execution tokens.

Typical use cases:

- browse underlyings that currently have derivatives
- inspect futures, options, and expiry calendars
- fetch lot size / tick size / segment metadata
- build an option chain grouped by strike

All queries run against the existing SQLite cache. If the DB has not yet been
seeded for the selected broker, callers receive a clear
``InstrumentStoreNotInitializedError`` directing them to initialize the main
client first.
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast

import aiosqlite

from tt_connect.core.exceptions import InstrumentNotFoundError, InstrumentStoreNotInitializedError
from tt_connect.core.models.enums import Exchange, OptionType
from tt_connect.core.models.instruments import (
    Commodity,
    Currency,
    Equity,
    Future,
    Index,
    Instrument,
    InstrumentInfo,
    Option,
    OptionChain,
    OptionChainEntry,
)


class InstrumentQueries:
    """Read-only query surface for the instrument cache.

    This class owns discovery-style lookups over the local SQLite database.
    It does not refresh data from brokers and does not participate in order
    execution token resolution.
    """

    def __init__(self, conn: aiosqlite.Connection | None) -> None:
        """Create a query helper bound to an optional SQLite connection."""
        self._conn = conn

    def bind(self, conn: aiosqlite.Connection | None) -> None:
        """Attach or detach the active SQLite connection."""
        self._conn = conn

    def _conn_or_raise(self) -> aiosqlite.Connection:
        """Return the active DB connection, or raise a store-specific error."""
        if self._conn is None:
            raise InstrumentStoreNotInitializedError(
                "Instrument DB not initialized. Initialize TTConnect or AsyncTTConnect first "
                "to seed or refresh instruments before using InstrumentStore."
            )
        return self._conn

    async def list_instruments(
        self,
        instrument_type: type[Instrument] | None = None,
        exchange: Exchange | None = None,
        underlying: Instrument | None = None,
        expiry: date | None = None,
        option_type: OptionType | None = None,
        strike: float | None = None,
        strike_min: float | None = None,
        strike_max: float | None = None,
        has_derivatives: bool | None = None,
        limit: int | None = 100,
    ) -> list[Instrument]:
        """List instruments using strict canonical filters.

        The filter language intentionally reuses the package's existing
        instrument objects and enums instead of introducing a separate query
        object. This keeps discovery aligned with the strict public model.
        """
        self._validate_list_filters(
            instrument_type=instrument_type,
            underlying=underlying,
            expiry=expiry,
            option_type=option_type,
            strike=strike,
            strike_min=strike_min,
            strike_max=strike_max,
            has_derivatives=has_derivatives,
            limit=limit,
        )

        if instrument_type in (Future,):
            return cast(
                list[Instrument],
                await self._list_futures(
                    exchange=exchange,
                    underlying=underlying,
                    expiry=expiry,
                    limit=limit,
                ),
            )
        if instrument_type in (Option,):
            return cast(
                list[Instrument],
                await self._list_options(
                    exchange=exchange,
                    underlying=underlying,
                    expiry=expiry,
                    option_type=option_type,
                    strike=strike,
                    strike_min=strike_min,
                    strike_max=strike_max,
                    limit=limit,
                ),
            )
        return cast(
            list[Instrument],
            await self._list_underlyings(
                instrument_type=instrument_type,
                exchange=exchange,
                has_derivatives=has_derivatives,
                limit=limit,
            ),
        )

    async def get_futures(self, underlying: Instrument) -> list[Future]:
        """Return all active futures for an underlying instrument, sorted by expiry."""
        futures = await self.list_instruments(
            instrument_type=Future,
            underlying=underlying,
            limit=None,
        )
        return [instrument for instrument in futures if isinstance(instrument, Future)]

    async def get_options(
        self,
        underlying: Instrument,
        expiry: date | None = None,
    ) -> list[Option]:
        """Return options for an underlying, optionally filtered by expiry.

        Results are sorted by expiry -> strike -> option_type (CE before PE).
        """
        options = await self.list_instruments(
            instrument_type=Option,
            underlying=underlying,
            expiry=expiry,
            limit=None,
        )
        return [instrument for instrument in options if isinstance(instrument, Option)]

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
    ) -> list[Equity | Index]:
        """Search underlyings (equities + indices) by symbol substring.

        Matching is case-insensitive. Results are sorted by exchange then
        symbol and capped at 50 rows.
        """
        pattern = f"%{query.upper()}%"
        if exchange is not None:
            sql = """
                SELECT i.exchange, i.symbol, i.segment
                FROM instruments i
                JOIN equities e ON e.instrument_id = i.id
                WHERE UPPER(i.symbol) LIKE ? AND i.exchange = ?
                ORDER BY i.exchange, i.symbol
                LIMIT 50
            """
            params: tuple[Any, ...] = (pattern, exchange)
        else:
            sql = """
                SELECT i.exchange, i.symbol, i.segment
                FROM instruments i
                JOIN equities e ON e.instrument_id = i.id
                WHERE UPPER(i.symbol) LIKE ?
                ORDER BY i.exchange, i.symbol
                LIMIT 50
            """
            params = (pattern,)
        async with self._conn_or_raise().execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [
            Index(exchange=Exchange(row[0]), symbol=row[1])
            if row[2] == "INDICES"
            else Equity(exchange=Exchange(row[0]), symbol=row[1])
            for row in rows
        ]

    async def get_instrument_info(self, instrument: Instrument) -> InstrumentInfo:
        """Return lot size, tick size, name and segment for any instrument.

        Raises:
            InstrumentNotFoundError: if the instrument is not present in the DB.
        """
        sql = """
            SELECT i.name, i.lot_size, i.tick_size, i.segment
            FROM instruments i
            WHERE i.exchange = ? AND i.symbol = ?
            LIMIT 1
        """
        async with self._conn_or_raise().execute(
            sql, (str(instrument.exchange), instrument.symbol)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            raise InstrumentNotFoundError(
                f"Instrument not found: {instrument.exchange}:{instrument.symbol}"
            )
        return InstrumentInfo(
            instrument=instrument,
            name=row[0],
            lot_size=int(row[1]),
            tick_size=float(row[2]),
            segment=row[3],
        )

    async def get_option_chain(self, underlying: Instrument, expiry: date) -> OptionChain:
        """Return all CE/PE pairs at every strike for a given underlying + expiry."""
        sql = """
            SELECT o.strike, o.option_type, opt.exchange, u.symbol
            FROM options o
            JOIN instruments opt ON opt.id = o.instrument_id
            JOIN instruments u ON u.id = o.underlying_id
            WHERE u.exchange = ? AND u.symbol = ? AND o.expiry = ?
            ORDER BY o.strike ASC, o.option_type ASC
        """
        async with self._conn_or_raise().execute(
            sql, (str(underlying.exchange), underlying.symbol, expiry.isoformat())
        ) as cur:
            rows = await cur.fetchall()

        strikes: dict[float, dict[str, Option]] = {}
        for row in rows:
            strike, option_type, u_exchange, u_symbol = row
            strike = float(strike)
            opt = Option(
                exchange=Exchange(u_exchange),
                symbol=u_symbol,
                expiry=expiry,
                strike=strike,
                option_type=OptionType(option_type),
            )
            strikes.setdefault(strike, {})[option_type] = opt

        entries = [
            OptionChainEntry(strike=strike, ce=side_map.get("CE"), pe=side_map.get("PE"))
            for strike, side_map in sorted(strikes.items())
        ]
        return OptionChain(underlying=underlying, expiry=expiry, entries=entries)

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute raw SQL against the instrument DB and return all rows.

        This is an escape hatch for advanced local discovery queries not covered
        by the typed methods above.
        """
        async with self._conn_or_raise().execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [tuple(row) for row in rows]

    def _validate_list_filters(
        self,
        *,
        instrument_type: type[Instrument] | None,
        underlying: Instrument | None,
        expiry: date | None,
        option_type: OptionType | None,
        strike: float | None,
        strike_min: float | None,
        strike_max: float | None,
        has_derivatives: bool | None,
        limit: int | None,
    ) -> None:
        if instrument_type in (Currency, Commodity):
            raise ValueError(
                "Currency and Commodity listings are not supported yet by the local instrument schema."
            )
        if instrument_type not in (None, Instrument, Equity, Index, Future, Option):
            raise TypeError("instrument_type must be one of Instrument, Equity, Index, Future, or Option.")
        if limit is not None and limit <= 0:
            raise ValueError("limit must be positive when provided.")
        if strike is not None and (strike_min is not None or strike_max is not None):
            raise ValueError("Use either strike or strike_min/strike_max, not both.")
        if strike_min is not None and strike_max is not None and strike_min > strike_max:
            raise ValueError("strike_min cannot be greater than strike_max.")
        if underlying is not None and instrument_type not in (Future, Option):
            raise ValueError("underlying filter is only valid for Future or Option listings.")
        if expiry is not None and instrument_type not in (Future, Option):
            raise ValueError("expiry filter is only valid for Future or Option listings.")
        if option_type is not None and instrument_type is not Option:
            raise ValueError("option_type filter is only valid for Option listings.")
        if any(value is not None for value in (strike, strike_min, strike_max)) and instrument_type is not Option:
            raise ValueError("strike filters are only valid for Option listings.")
        if has_derivatives is not None and instrument_type not in (None, Instrument, Equity, Index):
            raise ValueError("has_derivatives is only valid for underlying listings.")

    async def _list_underlyings(
        self,
        *,
        instrument_type: type[Instrument] | None,
        exchange: Exchange | None,
        has_derivatives: bool | None,
        limit: int | None,
    ) -> list[Equity | Index]:
        sql = """
            SELECT DISTINCT i.exchange, i.symbol, i.segment
            FROM instruments i
            JOIN equities e ON e.instrument_id = i.id
        """
        conditions: list[str] = []
        params: list[Any] = []

        if instrument_type is Index:
            conditions.append("i.segment = 'INDICES'")
        elif instrument_type is Equity:
            conditions.append("i.segment <> 'INDICES'")

        if exchange is not None:
            conditions.append("i.exchange = ?")
            params.append(str(exchange))

        if has_derivatives is True:
            conditions.append(
                "i.id IN (SELECT underlying_id FROM futures UNION SELECT underlying_id FROM options)"
            )
        elif has_derivatives is False:
            conditions.append(
                "i.id NOT IN (SELECT underlying_id FROM futures UNION SELECT underlying_id FROM options)"
            )

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY i.exchange, i.symbol"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        async with self._conn_or_raise().execute(sql, tuple(params)) as cur:
            rows = await cur.fetchall()
        return [
            Index(exchange=Exchange(row[0]), symbol=row[1])
            if row[2] == "INDICES"
            else Equity(exchange=Exchange(row[0]), symbol=row[1])
            for row in rows
        ]

    async def _list_futures(
        self,
        *,
        exchange: Exchange | None,
        underlying: Instrument | None,
        expiry: date | None,
        limit: int | None,
    ) -> list[Future]:
        sql = """
            SELECT fut.exchange, u.symbol, f.expiry
            FROM instruments fut
            JOIN futures f ON f.instrument_id = fut.id
            JOIN instruments u ON u.id = f.underlying_id
        """
        conditions: list[str] = []
        params: list[Any] = []

        if exchange is not None:
            conditions.append("fut.exchange = ?")
            params.append(str(exchange))
        if underlying is not None:
            conditions.append("u.exchange = ? AND u.symbol = ?")
            params.extend((str(underlying.exchange), underlying.symbol))
        if expiry is not None:
            conditions.append("f.expiry = ?")
            params.append(expiry.isoformat())

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY f.expiry ASC, fut.exchange ASC, u.symbol ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        async with self._conn_or_raise().execute(sql, tuple(params)) as cur:
            rows = await cur.fetchall()
        return [
            Future(
                exchange=Exchange(row[0]),
                symbol=row[1],
                expiry=date.fromisoformat(row[2]),
            )
            for row in rows
        ]

    async def _list_options(
        self,
        *,
        exchange: Exchange | None,
        underlying: Instrument | None,
        expiry: date | None,
        option_type: OptionType | None,
        strike: float | None,
        strike_min: float | None,
        strike_max: float | None,
        limit: int | None,
    ) -> list[Option]:
        sql = """
            SELECT opt.exchange, u.symbol, o.expiry, o.strike, o.option_type
            FROM instruments opt
            JOIN options o ON o.instrument_id = opt.id
            JOIN instruments u ON u.id = o.underlying_id
        """
        conditions: list[str] = []
        params: list[Any] = []

        if exchange is not None:
            conditions.append("opt.exchange = ?")
            params.append(str(exchange))
        if underlying is not None:
            conditions.append("u.exchange = ? AND u.symbol = ?")
            params.extend((str(underlying.exchange), underlying.symbol))
        if expiry is not None:
            conditions.append("o.expiry = ?")
            params.append(expiry.isoformat())
        if option_type is not None:
            conditions.append("o.option_type = ?")
            params.append(str(option_type))
        if strike is not None:
            conditions.append("o.strike = ?")
            params.append(strike)
        if strike_min is not None:
            conditions.append("o.strike >= ?")
            params.append(strike_min)
        if strike_max is not None:
            conditions.append("o.strike <= ?")
            params.append(strike_max)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY o.expiry ASC, o.strike ASC, o.option_type ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        async with self._conn_or_raise().execute(sql, tuple(params)) as cur:
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
