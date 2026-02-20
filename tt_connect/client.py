from __future__ import annotations
import asyncio
import threading
from tt_connect.adapters.base import BrokerAdapter
from tt_connect.enums import Side, ProductType, OrderType, OnStale
from tt_connect.instruments import Instrument
from tt_connect.instrument_manager.manager import InstrumentManager
from tt_connect.instrument_manager.resolver import InstrumentResolver
from tt_connect.models import Profile, Fund, Holding, Position, Order, Trade, Margin
from tt_connect.ws.client import WebSocketClient, OnTick


class AsyncTTConnect:
    def __init__(self, broker: str, config: dict):
        self._broker_id = broker
        self._adapter: BrokerAdapter = BrokerAdapter._registry[broker](config)
        self._instrument_manager = InstrumentManager(
            broker_id=broker,
            on_stale=config.get("on_stale", OnStale.FAIL),
        )
        self._resolver: InstrumentResolver | None = None
        self._ws: WebSocketClient | None = None

    async def init(self) -> None:
        await self._adapter.login()
        await self._instrument_manager.init(self._adapter.fetch_instruments)
        self._resolver = InstrumentResolver(
            self._instrument_manager.connection,
            self._broker_id,
        )

    async def close(self) -> None:
        await self._instrument_manager.connection.close()
        await self._adapter._client.aclose()

    async def _resolve(self, instrument: Instrument) -> str:
        assert self._resolver, "Call await broker.init() first"
        return await self._resolver.resolve(instrument)

    # --- Profile & Funds ---

    async def get_profile(self) -> Profile:
        raw = await self._adapter.get_profile()
        return self._adapter.transformer.to_profile(raw["data"])

    async def get_funds(self) -> Fund:
        raw = await self._adapter.get_funds()
        return self._adapter.transformer.to_fund(raw["data"])

    # --- Portfolio ---

    async def get_holdings(self) -> list[Holding]:
        raw = await self._adapter.get_holdings()
        return [self._adapter.transformer.to_holding(h) for h in raw["data"]]

    async def get_positions(self) -> list[Position]:
        raw = await self._adapter.get_positions()
        return [self._adapter.transformer.to_position(p) for p in raw["data"]]

    # --- Reports ---

    async def get_trades(self) -> list[Trade]:
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
        self._adapter.capabilities.verify(instrument, order_type, product)
        token = await self._resolve(instrument)
        params = self._adapter.transformer.to_order_params(
            token, qty, side, product, order_type, price, trigger_price
        )
        raw = await self._adapter.place_order(params)
        return raw["data"]["order_id"]

    async def modify_order(self, order_id: str, **kwargs) -> None:
        await self._adapter.modify_order(order_id, kwargs)

    async def cancel_order(self, order_id: str) -> None:
        await self._adapter.cancel_order(order_id)

    async def cancel_all_orders(self) -> tuple[list[str], list[str]]:
        """Cancel every open order. Returns (cancelled_ids, failed_ids)."""
        raw = await self._adapter.get_orders()
        open_statuses = {"OPEN", "TRIGGER PENDING", "AMO REQ RECEIVED",
                         "MODIFY PENDING", "OPEN PENDING", "CANCEL PENDING",
                         "VALIDATION PENDING"}
        open_orders = [o for o in raw["data"] if o["status"] in open_statuses]

        cancelled, failed = [], []
        for order in open_orders:
            oid = order["order_id"]
            try:
                await self._adapter.cancel_order(oid)
                cancelled.append(oid)
            except Exception:
                failed.append(oid)
        return cancelled, failed

    async def close_all_positions(self) -> tuple[list[str], list[str]]:
        """
        Place offsetting market orders for every open position.
        Returns (placed_order_ids, failed_symbols).
        """
        raw = await self._adapter.get_positions()
        placed, failed = [], []
        for pos in raw["data"]:
            qty = pos["quantity"]
            if qty == 0:
                continue
            side = Side.SELL if qty > 0 else Side.BUY
            params = self._adapter.transformer.to_order_params(
                instrument_token=pos["tradingsymbol"],
                qty=abs(qty),
                side=side,
                product=ProductType(pos["product"]),
                order_type=OrderType.MARKET,
                price=None,
                trigger_price=None,
            )
            try:
                result = await self._adapter.place_order(params)
                placed.append(result["data"]["order_id"])
            except Exception:
                failed.append(pos["tradingsymbol"])
        return placed, failed

    async def get_order(self, order_id: str) -> Order:
        raw = await self._adapter.get_order(order_id)
        return self._adapter.transformer.to_order(raw["data"], instrument=None)

    async def get_orders(self) -> list[Order]:
        raw = await self._adapter.get_orders()
        return [self._adapter.transformer.to_order(o, instrument=None) for o in raw["data"]]

    # --- Streaming ---

    async def subscribe(
        self,
        instruments: list[Instrument],
        on_tick: OnTick,
        on_order_update: OnTick | None = None,
    ) -> None:
        if not self._ws:
            self._ws = WebSocketClient(self._broker_id, self._adapter.auth)
        await self._ws.subscribe(instruments, on_tick, on_order_update)


class TTConnect:
    def __init__(self, broker: str, config: dict):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncTTConnect(broker, config)
        self._run(self._async.init())

    def _run(self, coro):
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

    def place_order(self, instrument: Instrument, qty: int, side: Side,
                    product: ProductType, order_type: OrderType,
                    price: float | None = None,
                    trigger_price: float | None = None) -> str:
        return self._run(self._async.place_order(
            instrument, qty, side, product, order_type, price, trigger_price
        ))

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
