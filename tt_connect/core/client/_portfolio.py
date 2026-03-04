"""Portfolio mixin: profile, funds, holdings, positions, trades, and historical OHLC."""

from __future__ import annotations

from datetime import datetime

from tt_connect.core.adapter.transformer import JsonDict
from tt_connect.core.models.enums import CandleInterval
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.client._lifecycle import _ClientBase
from tt_connect.core.models import Candle, Fund, GetHistoricalRequest, Holding, Position, Profile, Tick, Trade


class PortfolioMixin(_ClientBase):
    """Read-only portfolio and account data methods."""

    async def get_profile(self) -> Profile:
        """Fetch and normalize account profile."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_profile()
        return self._adapter.transformer.to_profile(raw["data"])

    async def get_funds(self) -> Fund:
        """Fetch and normalize available/used funds."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_funds()
        return self._adapter.transformer.to_fund(raw["data"])

    async def get_holdings(self) -> list[Holding]:
        """Fetch and normalize demat holdings."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_holdings()
        return [self._adapter.transformer.to_holding(h) for h in raw["data"]]

    async def get_positions(self) -> list[Position]:
        """Fetch and normalize open net positions."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_positions()
        return [self._adapter.transformer.to_position(p) for p in raw["data"]]

    async def get_trades(self) -> list[Trade]:
        """Fetch and normalize trade-book entries."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_trades()
        return [self._adapter.transformer.to_trade(t) for t in raw["data"]]

    async def get_quotes(self, instruments: list[Instrument]) -> list[Tick]:
        """Fetch an LTP/volume/OI market snapshot for one or more instruments.

        Resolves each instrument to its broker token, requests the Zerodha
        /quote endpoint in a single call, and returns one Tick per instrument.
        Keys absent from the broker response are silently omitted.
        """
        self._require_connected()
        resolved_list = [await self._resolve(inst) for inst in instruments]
        keys = [f"{r.exchange}:{r.broker_symbol}" for r in resolved_list]
        key_to_inst: dict[str, Instrument] = dict(zip(keys, instruments))
        raw: JsonDict = await self._adapter.get_quotes(keys)
        return [
            self._adapter.transformer.to_quote(raw["data"][key], inst)
            for key, inst in key_to_inst.items()
            if key in raw["data"]
        ]

    async def get_historical(
        self,
        instrument: Instrument,
        interval: CandleInterval,
        from_date: datetime,
        to_date: datetime,
    ) -> list[Candle]:
        """Fetch historical OHLC candles for an instrument."""
        self._require_connected()
        resolved = await self._resolve(instrument)
        req = GetHistoricalRequest(
            instrument=instrument,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
        )
        params: JsonDict = self._adapter.transformer.to_historical_params(
            resolved.token, resolved.broker_symbol, resolved.exchange, req,
        )
        raw: JsonDict = await self._adapter.get_historical(resolved.token, params)
        return self._adapter.transformer.to_candles(raw["data"], instrument)
