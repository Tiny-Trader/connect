from __future__ import annotations
import asyncio
import threading
from tt_connect.adapters.base import BrokerAdapter
from tt_connect.enums import Side, ProductType, OrderType, OrderStatus, OnStale
from tt_connect.instruments import Instrument
from tt_connect.instrument_manager.manager import InstrumentManager
from tt_connect.instrument_manager.resolver import InstrumentResolver
from tt_connect.models import Profile, Fund, Holding, Position, Order, Trade
from tt_connect.ws.client import BrokerWebSocket, OnTick


class AsyncTTConnect:
    """Async-first public client for normalized broker operations.

    Lifecycle:
    1. Construct with broker id and config.
    2. Call :meth:`init` once before any read/write operation.
    3. Call :meth:`close` to release HTTP, DB, and WebSocket resources.
    """

    def __init__(self, broker: str, config: dict):
        self._broker_id = broker
        self._adapter: BrokerAdapter = BrokerAdapter._registry[broker](config)
        self._instrument_manager = InstrumentManager(
            broker_id=broker,
            on_stale=config.get("on_stale", OnStale.FAIL),
        )
        self._resolver: InstrumentResolver | None = None
        self._ws: BrokerWebSocket | None = None

    async def init(self) -> None:
        """Authenticate and initialize a fresh/stale-safe instrument resolver."""
        await self._adapter.login()
        await self._instrument_manager.init(self._adapter.fetch_instruments)
        self._resolver = InstrumentResolver(
            self._instrument_manager.connection,
            self._broker_id,
        )

    async def close(self) -> None:
        """Close WebSocket (if open), instrument DB connection, and HTTP client."""
        if self._ws:
            await self._ws.close()
        await self._instrument_manager.connection.close()
        await self._adapter._client.aclose()

    async def _resolve(self, instrument: Instrument):
        """Resolve a canonical instrument to broker token/symbol/exchange."""
        assert self._resolver, "Call await broker.init() first"
        return await self._resolver.resolve(instrument)

    # --- Profile & Funds ---

    async def get_profile(self) -> Profile:
        """Fetch and normalize account profile."""
        raw = await self._adapter.get_profile()
        return self._adapter.transformer.to_profile(raw["data"])

    async def get_funds(self) -> Fund:
        """Fetch and normalize available/used funds."""
        raw = await self._adapter.get_funds()
        return self._adapter.transformer.to_fund(raw["data"])

    # --- Portfolio ---

    async def get_holdings(self) -> list[Holding]:
        """Fetch and normalize demat holdings."""
        raw = await self._adapter.get_holdings()
        return [self._adapter.transformer.to_holding(h) for h in raw["data"]]

    async def get_positions(self) -> list[Position]:
        """Fetch and normalize open net positions."""
        raw = await self._adapter.get_positions()
        return [self._adapter.transformer.to_position(p) for p in raw["data"]]

    # --- Reports ---

    async def get_trades(self) -> list[Trade]:
        """Fetch and normalize trade-book entries."""
        raw = await self._adapter.get_trades()
        return [self._adapter.transformer.to_trade(t) for t in raw["data"]]

    # --- Orders ---

    async def place_order(
        self,
        instrument: Instrument,
        qty: int,
        side: Side,
        product: ProductType,
        order_type: OrderType,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> str:
        """Place an order after capability checks and instrument resolution.

        Returns:
            Broker order id.
        """
        self._adapter.capabilities.verify(instrument, order_type, product)
        resolved = await self._resolve(instrument)
        params = self._adapter.transformer.to_order_params(
            resolved.token,
            resolved.broker_symbol,
            resolved.exchange,
            qty,
            side,
            product,
            order_type,
            price,
            trigger_price,
        )
        raw = await self._adapter.place_order(params)
        return self._adapter.transformer.to_order_id(raw)

    async def modify_order(self, order_id: str, **kwargs) -> None:
        """Modify an existing order using broker-specific raw kwargs."""
        await self._adapter.modify_order(order_id, kwargs)

    async def cancel_order(self, order_id: str) -> None:
        """Cancel a single order by id."""
        await self._adapter.cancel_order(order_id)

    async def cancel_all_orders(self) -> tuple[list[str], list[str]]:
        """Cancel every open order. Returns (cancelled_ids, failed_ids)."""
        orders = await self.get_orders()
        open_orders = [o for o in orders if o.status in {OrderStatus.OPEN, OrderStatus.PENDING}]
        cancelled, failed = [], []
        for order in open_orders:
            try:
                await self._adapter.cancel_order(order.id)
                cancelled.append(order.id)
            except Exception:
                failed.append(order.id)
        return cancelled, failed

    async def close_all_positions(self) -> tuple[list[str], list[str]]:
        """
        Place offsetting market orders for every open position.
        Returns (placed_order_ids, failed_symbols).
        """
        raw = await self._adapter.get_positions()
        placed, failed = [], []
        for pos_raw in raw["data"]:
            position = self._adapter.transformer.to_position(pos_raw)
            if position.qty == 0:
                continue
            side = Side.SELL if position.qty > 0 else Side.BUY
            params = self._adapter.transformer.to_close_position_params(
                pos_raw, abs(position.qty), side
            )
            try:
                result = await self._adapter.place_order(params)
                placed.append(self._adapter.transformer.to_order_id(result))
            except Exception:
                failed.append(pos_raw.get("tradingsymbol", "unknown"))
        return placed, failed

    async def get_order(self, order_id: str) -> Order:
        """Fetch a single order and normalize it to the canonical model."""
        raw = await self._adapter.get_order(order_id)
        return self._adapter.transformer.to_order(raw["data"], instrument=None)

    async def get_orders(self) -> list[Order]:
        """Fetch and normalize all orders."""
        raw = await self._adapter.get_orders()
        return [self._adapter.transformer.to_order(o, instrument=None) for o in raw["data"]]

    # --- Streaming ---

    async def subscribe(
        self,
        instruments: list[Instrument],
        on_tick: OnTick,
    ) -> None:
        """Subscribe to ticks for canonical instruments.

        Each instrument is resolved to broker token metadata before subscription.
        """
        if not self._ws:
            self._ws = self._adapter.create_ws_client()
        # Resolve each instrument to get broker token + symbol + exchange
        subscriptions = [
            (instrument, await self._resolve(instrument)) for instrument in instruments
        ]
        await self._ws.subscribe(subscriptions, on_tick)

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        """Unsubscribe previously subscribed instruments."""
        if self._ws:
            await self._ws.unsubscribe(instruments)


class TTConnect:
    """Threaded synchronous wrapper over :class:`AsyncTTConnect`."""

    def __init__(self, broker: str, config: dict):
        """Create a dedicated event loop thread and initialize the async client."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncTTConnect(broker, config)
        self._run(self._async.init())

    def _run(self, coro):
        """Execute a coroutine on the internal loop and block for result."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def get_profile(self) -> Profile:
        return self._run(self._async.get_profile())

    def get_funds(self) -> Fund:
        return self._run(self._async.get_funds())

    def get_holdings(self) -> list[Holding]:
        return self._run(self._async.get_holdings())

    def get_positions(self) -> list[Position]:
        return self._run(self._async.get_positions())

    def get_trades(self) -> list[Trade]:
        return self._run(self._async.get_trades())

    def place_order(
        self,
        instrument: Instrument,
        qty: int,
        side: Side,
        product: ProductType,
        order_type: OrderType,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> str:
        return self._run(
            self._async.place_order(
                instrument, qty, side, product, order_type, price, trigger_price
            )
        )

    def modify_order(self, order_id: str, **kwargs) -> None:
        self._run(self._async.modify_order(order_id, **kwargs))

    def cancel_order(self, order_id: str) -> None:
        self._run(self._async.cancel_order(order_id))

    def cancel_all_orders(self) -> tuple[list[str], list[str]]:
        return self._run(self._async.cancel_all_orders())

    def close_all_positions(self) -> tuple[list[str], list[str]]:
        return self._run(self._async.close_all_positions())

    def get_order(self, order_id: str) -> Order:
        return self._run(self._async.get_order(order_id))

    def get_orders(self) -> list[Order]:
        return self._run(self._async.get_orders())
