"""Async-first unified broker client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from tt_connect.core.models.enums import CandleInterval
from tt_connect.core.models.instruments import Equity, Future, Instrument, Option
from tt_connect.core.client._lifecycle import LifecycleMixin
from tt_connect.core.models import (
    Candle,
    Fund,
    Gtt,
    Holding,
    ModifyGttRequest,
    ModifyOrderRequest,
    Order,
    PlaceGttRequest,
    PlaceOrderRequest,
    Position,
    Profile,
    Tick,
    Trade,
)
from tt_connect.core.client._orders import OrdersMixin
from tt_connect.core.client._portfolio import PortfolioMixin
from tt_connect.core.client._sync import TTConnect
from tt_connect.core.client._instruments import InstrumentsMixin
from tt_connect.core.adapter.ws import OnTick

__all__ = ["AsyncTTConnect", "TTConnect"]


class _AsyncTTConnectCore(LifecycleMixin, PortfolioMixin, OrdersMixin, InstrumentsMixin):
    """Internal implementation class. Use :class:`AsyncTTConnect` publicly."""


class AsyncTTConnect:
    """Async-first public client for normalized broker operations.

    Lifecycle:
    1. Construct with broker id and config.
    2. Call :meth:`init` once before any read/write operation.
    3. Call :meth:`close` to release HTTP, DB, and WebSocket resources.

    Can also be used as an async context manager::

        async with AsyncTTConnect("zerodha", config) as client:
            profile = await client.get_profile()
    """

    def __init__(self, broker: str, config: dict[str, Any]) -> None:
        self._core = _AsyncTTConnectCore(broker, config)

    def __dir__(self) -> list[str]:
        return [
            name
            for name in super().__dir__()
            if not (name.startswith("_") and not name.startswith("__"))
        ]

    async def __aenter__(self) -> "AsyncTTConnect":
        await self._core.init()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self._core.close()

    # --- Lifecycle ---

    async def init(self) -> None:
        """Authenticate and initialize a fresh/stale-safe instrument resolver."""
        await self._core.init()

    async def close(self) -> None:
        """Close WebSocket (if open), instrument DB connection, and HTTP client."""
        await self._core.close()

    async def subscribe(self, instruments: list[Instrument], on_tick: OnTick) -> None:
        """Subscribe to ticks for canonical instruments."""
        await self._core.subscribe(instruments, on_tick)

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        """Unsubscribe previously subscribed instruments."""
        await self._core.unsubscribe(instruments)

    # --- Portfolio ---

    async def get_profile(self) -> Profile:
        """Fetch and normalize account profile."""
        return await self._core.get_profile()

    async def get_funds(self) -> Fund:
        """Fetch and normalize available/used funds."""
        return await self._core.get_funds()

    async def get_holdings(self) -> list[Holding]:
        """Fetch and normalize demat holdings."""
        return await self._core.get_holdings()

    async def get_positions(self) -> list[Position]:
        """Fetch and normalize open net positions."""
        return await self._core.get_positions()

    async def get_trades(self) -> list[Trade]:
        """Fetch and normalize trade-book entries."""
        return await self._core.get_trades()

    async def get_quotes(self, instruments: list[Instrument]) -> list[Tick]:
        """Fetch an LTP/volume/OI market snapshot for one or more instruments."""
        return await self._core.get_quotes(instruments)

    async def get_historical(
        self,
        instrument: Instrument,
        interval: CandleInterval,
        from_date: datetime,
        to_date: datetime,
    ) -> list[Candle]:
        """Fetch historical OHLC candles for an instrument."""
        return await self._core.get_historical(instrument, interval, from_date, to_date)

    # --- Orders ---

    async def place_order(self, req: PlaceOrderRequest) -> str:
        """Place an order. Returns broker order id."""
        return await self._core.place_order(req)

    async def modify_order(self, req: ModifyOrderRequest) -> None:
        """Modify an existing order."""
        await self._core.modify_order(req)

    async def cancel_order(self, order_id: str) -> None:
        """Cancel a single order by id."""
        await self._core.cancel_order(order_id)

    async def cancel_all_orders(self) -> tuple[list[str], list[str]]:
        """Cancel every open order. Returns (cancelled_ids, failed_ids)."""
        return await self._core.cancel_all_orders()

    async def get_order(self, order_id: str) -> Order:
        """Fetch a single order and normalize it to the canonical model."""
        return await self._core.get_order(order_id)

    async def get_orders(self) -> list[Order]:
        """Fetch and normalize all orders."""
        return await self._core.get_orders()

    async def place_gtt(self, req: PlaceGttRequest) -> str:
        """Place a GTT rule and return the broker GTT id."""
        return await self._core.place_gtt(req)

    async def modify_gtt(self, req: ModifyGttRequest) -> None:
        """Modify an existing GTT rule."""
        await self._core.modify_gtt(req)

    async def cancel_gtt(self, gtt_id: str) -> None:
        """Cancel / delete a GTT rule by id."""
        await self._core.cancel_gtt(gtt_id)

    async def get_gtt(self, gtt_id: str) -> Gtt:
        """Fetch and normalize a single GTT rule."""
        return await self._core.get_gtt(gtt_id)

    async def get_gtts(self) -> list[Gtt]:
        """Fetch and normalize all GTT rules."""
        return await self._core.get_gtts()

    async def close_all_positions(self) -> tuple[list[str], list[str]]:
        """Place offsetting market orders for every open position."""
        return await self._core.close_all_positions()

    # --- Instrument helpers ---

    async def get_futures(self, instrument: Instrument) -> list[Future]:
        """Return all active futures for the given underlying, sorted by expiry."""
        return await self._core.get_futures(instrument)

    async def get_options(
        self,
        instrument: Instrument,
        expiry: date | None = None,
    ) -> list[Option]:
        """Return options for the given underlying, optionally filtered by expiry."""
        return await self._core.get_options(instrument, expiry)

    async def get_expiries(self, instrument: Instrument) -> list[date]:
        """Return all distinct expiry dates for an underlying."""
        return await self._core.get_expiries(instrument)

    async def search_instruments(
        self,
        query: str,
        exchange: str | None = None,
    ) -> list[Equity]:
        """Search underlyings by symbol substring (case-insensitive)."""
        return await self._core.search_instruments(query, exchange)
