"""Portfolio mixin: profile, funds, holdings, positions, and trades."""

from __future__ import annotations

from tt_connect.adapters.base import JsonDict
from tt_connect.lifecycle import _ClientBase
from tt_connect.models import Fund, Holding, Position, Profile, Trade


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
