"""Canonical instrument to broker token/symbol resolver."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
from tt_connect.instruments import Instrument, Index, Equity, Future, Option
from tt_connect.exceptions import InstrumentNotFoundError


@dataclass(frozen=True)
class ResolvedInstrument:
    """All broker-specific fields needed to place an order."""
    token: str          # numeric broker token (symboltoken for AngelOne)
    broker_symbol: str  # broker's own tradingsymbol (e.g. "NIFTY30MAR26FUT")
    exchange: str       # exchange on which this instrument trades (NSE, NFO, BSE, BFO)


class InstrumentResolver:
    """Resolve canonical instruments to broker-specific execution metadata."""

    def __init__(self, conn: aiosqlite.Connection, broker_id: str):
        self._conn = conn
        self._broker_id = broker_id
        self._cache: dict[Instrument, ResolvedInstrument] = {}

    async def resolve(self, instrument: Instrument) -> ResolvedInstrument:
        """Resolve with an in-memory cache to avoid repeated DB lookups."""
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
        """Resolve index instruments from `INDICES` rows."""
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
        """Resolve non-index equities."""
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
        """Resolve futures by underlying identity and expiry date."""
        # instrument.exchange is the underlying's exchange (NSE/BSE), not NFO/BFO.
        # Join through the underlying to match on what the user actually knows.
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
        """Resolve options by underlying, expiry, strike, and CE/PE side."""
        # instrument.exchange is the underlying's exchange (NSE/BSE), not NFO/BFO.
        # Join through the underlying to match on what the user actually knows.
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
