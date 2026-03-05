"""Canonical instrument to broker token/symbol resolver.

Translates user-facing Instrument objects (which carry only canonical
identifiers like exchange + symbol + expiry) into the broker-specific
execution metadata (numeric token, broker tradingsymbol, derivative
exchange) needed to place orders and subscribe to streams.

Resolution is backed by the SQLite instrument store and cached in memory
for the lifetime of the resolver to avoid repeated DB lookups.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
from tt_connect.core.models.instruments import Instrument, Index, Equity, Future, Option
from tt_connect.core.exceptions import InstrumentNotFoundError


@dataclass(frozen=True)
class ResolvedInstrument:
    """Broker-specific execution metadata for a resolved instrument.

    Returned by ``InstrumentResolver.resolve()`` and consumed by the
    adapter (for REST params) and the WebSocket client (for subscriptions).
    """

    token: str
    """Broker's numeric instrument token (e.g. ``"256265"`` for Zerodha,
    ``"99926000"`` for AngelOne). Passed as the security identifier in
    order placement and historical data requests."""

    broker_symbol: str
    """Broker's own trading symbol (e.g. ``"NIFTY 50"``, ``"NIFTY26MARFUT"``,
    ``"RELIANCE"``) -- used in order params and response matching."""

    exchange: str
    """Exchange segment on which this specific instrument trades.
    For derivatives this is the derivative exchange (``"NFO"``, ``"BFO"``),
    not the underlying's cash exchange."""


class InstrumentResolver:
    """Resolve canonical Instrument objects to broker-specific tokens.

    The resolver queries the SQLite instrument store and maintains an
    in-memory cache so that repeated lookups for the same instrument
    (common during order placement and streaming) avoid DB round-trips.

    Resolution dispatches by instrument subtype:

    - ``Index``  -- ``INDICES`` segment rows
    - ``Equity`` -- non-index equity rows
    - ``Future`` -- joined through underlying + expiry
    - ``Option`` -- joined through underlying + expiry + strike + CE/PE
    """

    def __init__(self, conn: aiosqlite.Connection, broker_id: str):
        """Create a resolver bound to a specific broker's instrument data.

        Args:
            conn: Active aiosqlite connection to the instrument store DB.
            broker_id: Broker identifier used to filter ``broker_tokens``
                rows (each instrument may have tokens from multiple brokers).
        """
        self._conn = conn
        self._broker_id = broker_id
        self._cache: dict[Instrument, ResolvedInstrument] = {}

    async def resolve(self, instrument: Instrument) -> ResolvedInstrument:
        """Resolve a canonical instrument to broker-specific metadata.

        Results are cached in memory for the resolver's lifetime.

        Args:
            instrument: Any canonical instrument (Equity, Index, Future, Option).

        Returns:
            A ``ResolvedInstrument`` with broker token, symbol, and exchange.

        Raises:
            InstrumentNotFoundError: If no matching row exists in the store.
        """
        if instrument in self._cache:
            return self._cache[instrument]
        resolved = await self._resolve(instrument)
        self._cache[instrument] = resolved
        return resolved

    async def _resolve(self, instrument: Instrument) -> ResolvedInstrument:
        """Dispatch resolution by instrument subtype."""
        if isinstance(instrument, Index):
            return await self._resolve_index(instrument)
        if isinstance(instrument, Equity):
            return await self._resolve_equity(instrument)
        if isinstance(instrument, Future):
            return await self._resolve_future(instrument)
        if isinstance(instrument, Option):
            return await self._resolve_option(instrument)
        raise InstrumentNotFoundError(f"Unsupported instrument type: {type(instrument)}")

    async def _resolve_index(self, instrument: Index) -> ResolvedInstrument:
        """Resolve an index by matching ``exchange + symbol`` in the ``INDICES`` segment."""
        query = """
            SELECT bt.token, bt.broker_symbol, i.exchange
            FROM instruments i
            JOIN equities e ON e.instrument_id = i.id
            JOIN broker_tokens bt ON bt.instrument_id = i.id
            WHERE i.exchange = ? AND i.symbol = ? AND i.segment = 'INDICES' AND bt.broker_id = ?
        """
        async with self._conn.execute(query, (instrument.exchange, instrument.symbol, self._broker_id)) as cur:
            row = await cur.fetchone()
        if not row:
            raise InstrumentNotFoundError(f"No index found: {instrument.exchange}:{instrument.symbol}")
        return ResolvedInstrument(token=row[0], broker_symbol=row[1], exchange=row[2])

    async def _resolve_equity(self, instrument: Equity) -> ResolvedInstrument:
        """Resolve a cash equity by matching ``exchange + symbol``, excluding index rows."""
        query = """
            SELECT bt.token, bt.broker_symbol, i.exchange
            FROM instruments i
            JOIN equities e ON e.instrument_id = i.id
            JOIN broker_tokens bt ON bt.instrument_id = i.id
            WHERE i.exchange = ? AND i.symbol = ? AND i.segment != 'INDICES' AND bt.broker_id = ?
        """
        async with self._conn.execute(query, (instrument.exchange, instrument.symbol, self._broker_id)) as cur:
            row = await cur.fetchone()
        if not row:
            raise InstrumentNotFoundError(f"No equity found: {instrument.exchange}:{instrument.symbol}")
        return ResolvedInstrument(token=row[0], broker_symbol=row[1], exchange=row[2])

    async def _resolve_future(self, instrument: Future) -> ResolvedInstrument:
        """Resolve a future by underlying identity and expiry date.

        The user specifies the underlying's exchange (NSE/BSE) and symbol.
        The query joins through ``futures.underlying_id`` to find the
        derivative row on NFO/BFO with the matching expiry.
        """
        query = """
            SELECT bt.token, bt.broker_symbol, fut.exchange
            FROM instruments fut
            JOIN futures f        ON f.instrument_id  = fut.id
            JOIN instruments u    ON u.id             = f.underlying_id
            JOIN broker_tokens bt ON bt.instrument_id = fut.id
            WHERE u.exchange = ? AND u.symbol = ? AND f.expiry = ? AND bt.broker_id = ?
        """
        async with self._conn.execute(query, (
            instrument.exchange, instrument.symbol, instrument.expiry.isoformat(), self._broker_id
        )) as cur:
            row = await cur.fetchone()
        if not row:
            raise InstrumentNotFoundError(
                f"No future found: {instrument.exchange}:{instrument.symbol} {instrument.expiry}"
            )
        return ResolvedInstrument(token=row[0], broker_symbol=row[1], exchange=row[2])

    async def _resolve_option(self, instrument: Option) -> ResolvedInstrument:
        """Resolve an option by underlying, expiry, strike price, and option type.

        Same join strategy as ``_resolve_future`` -- the user provides the
        underlying's exchange/symbol, plus ``expiry``, ``strike``, and
        ``option_type`` (CE/PE) to uniquely identify the contract.
        """
        query = """
            SELECT bt.token, bt.broker_symbol, opt.exchange
            FROM instruments opt
            JOIN options o        ON o.instrument_id  = opt.id
            JOIN instruments u    ON u.id             = o.underlying_id
            JOIN broker_tokens bt ON bt.instrument_id = opt.id
            WHERE u.exchange = ? AND u.symbol = ? AND o.expiry = ?
              AND o.strike = ? AND o.option_type = ? AND bt.broker_id = ?
        """
        async with self._conn.execute(query, (
            instrument.exchange, instrument.symbol, instrument.expiry.isoformat(),
            instrument.strike, instrument.option_type, self._broker_id
        )) as cur:
            row = await cur.fetchone()
        if not row:
            raise InstrumentNotFoundError(
                f"No option found: {instrument.exchange}:{instrument.symbol} "
                f"{instrument.expiry} {instrument.strike}{instrument.option_type}"
            )
        return ResolvedInstrument(token=row[0], broker_symbol=row[1], exchange=row[2])
