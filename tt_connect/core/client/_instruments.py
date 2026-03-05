"""Instruments mixin: instrument-master query helpers exposed on the client."""

from __future__ import annotations

from datetime import date

from tt_connect.core.models.instruments import Equity, Future, Instrument, Option
from tt_connect.core.client._base import _ClientBase


class InstrumentsMixin(_ClientBase):
    """Instrument master query methods: futures, options, and expiry lookups."""

    async def get_futures(self, instrument: Instrument) -> list[Future]:
        """Return all active futures for the given underlying, sorted by expiry.

        Example::

            sbin = Equity(exchange="NSE", symbol="SBIN")
            futures = await client.get_futures(sbin)
            # → [Future(exchange=NSE, symbol='SBIN', expiry=date(2025, 3, 27)), ...]
        """
        self._require_connected()
        return await self._instrument_manager.get_futures(instrument)

    async def get_options(
        self,
        instrument: Instrument,
        expiry: date | None = None,
    ) -> list[Option]:
        """Return options for the given underlying, optionally filtered by expiry.

        Results are sorted by expiry → strike → option_type (CE before PE).

        Example::

            sbin  = Equity(exchange="NSE", symbol="SBIN")
            expiry = date(2025, 3, 27)
            chain = await client.get_options(sbin, expiry=expiry)
            # → [Option(..., strike=700.0, option_type='CE'),
            #    Option(..., strike=700.0, option_type='PE'), ...]
        """
        self._require_connected()
        return await self._instrument_manager.get_options(instrument, expiry)

    async def get_expiries(self, instrument: Instrument) -> list[date]:
        """Return all distinct expiry dates available for an underlying.

        Covers both futures and options expiries, sorted ascending.

        Example::

            nifty = Index(exchange="NSE", symbol="NIFTY 50")
            dates = await client.get_expiries(nifty)
            # → [date(2025, 1, 30), date(2025, 2, 27), ...]
        """
        self._require_connected()
        return await self._instrument_manager.get_expiries(instrument)

    async def search_instruments(
        self,
        query: str,
        exchange: str | None = None,
    ) -> list[Equity]:
        """Search the instrument master by symbol substring (case-insensitive).

        Returns up to 50 matching underlyings sorted by exchange then symbol.

        Example::

            results = await client.search_instruments("RELIANCE")
            # → [Equity(exchange=BSE, symbol='RELIANCE'),
            #    Equity(exchange=NSE, symbol='RELIANCE')]

            results = await client.search_instruments("REL", exchange="NSE")
            # → [Equity(exchange=NSE, symbol='RELIANCE')]
        """
        self._require_connected()
        return await self._instrument_manager.search_instruments(query, exchange)

