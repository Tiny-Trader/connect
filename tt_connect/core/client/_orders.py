"""Orders mixin: place, modify, cancel, and query orders and positions."""

from __future__ import annotations

from tt_connect.core.adapter.transformer import JsonDict
from tt_connect.core.models.enums import OrderStatus, Side
from tt_connect.core.client._lifecycle import _ClientBase
from tt_connect.core.models import Gtt, ModifyGttRequest, ModifyOrderRequest, Order, PlaceGttRequest, PlaceOrderRequest


class OrdersMixin(_ClientBase):
    """Order management and position closing methods."""

    async def place_order(self, req: PlaceOrderRequest) -> str:
        """Place an order after capability checks and instrument resolution.

        Returns:
            Broker order id.
        """
        self._require_connected()
        self._adapter.capabilities.verify(req.instrument, req.order_type, req.product)
        resolved = await self._resolve(req.instrument)
        params = self._adapter.transformer.to_order_params(
            resolved.token,
            resolved.broker_symbol,
            resolved.exchange,
            req,
        )
        raw = await self._adapter.place_order(params)
        return self._adapter.transformer.to_order_id(raw)

    async def modify_order(self, req: ModifyOrderRequest) -> None:
        """Modify an existing order using a canonical ModifyOrderRequest."""
        self._require_connected()
        params = self._adapter.transformer.to_modify_params(req)
        await self._adapter.modify_order(req.order_id, params)

    async def cancel_order(self, order_id: str) -> None:
        """Cancel a single order by id."""
        self._require_connected()
        await self._adapter.cancel_order(order_id)

    async def cancel_all_orders(self) -> tuple[list[str], list[str]]:
        """Cancel every open order. Returns (cancelled_ids, failed_ids)."""
        self._require_connected()
        orders = await self.get_orders()
        open_orders = [o for o in orders if o.status in {OrderStatus.OPEN, OrderStatus.PENDING}]
        cancelled: list[str] = []
        failed: list[str] = []
        for order in open_orders:
            try:
                await self._adapter.cancel_order(order.id)
                cancelled.append(order.id)
            except Exception:
                failed.append(order.id)
        return cancelled, failed

    async def get_order(self, order_id: str) -> Order:
        """Fetch a single order and normalize it to the canonical model."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_order(order_id)
        return self._adapter.transformer.to_order(raw["data"], instrument=None)

    async def get_orders(self) -> list[Order]:
        """Fetch and normalize all orders."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_orders()
        return [self._adapter.transformer.to_order(o, instrument=None) for o in raw["data"]]

    # --- GTT ---

    async def place_gtt(self, req: PlaceGttRequest) -> str:
        """Place a GTT rule and return the broker GTT id."""
        self._require_connected()
        resolved = await self._resolve(req.instrument)
        params = self._adapter.transformer.to_gtt_params(
            resolved.token, resolved.broker_symbol, resolved.exchange, req
        )
        raw = await self._adapter.place_gtt(params)
        return self._adapter.transformer.to_gtt_id(raw)

    async def modify_gtt(self, req: ModifyGttRequest) -> None:
        """Modify an existing GTT rule."""
        self._require_connected()
        resolved = await self._resolve(req.instrument)
        params = self._adapter.transformer.to_modify_gtt_params(
            resolved.token, resolved.broker_symbol, resolved.exchange, req
        )
        await self._adapter.modify_gtt(req.gtt_id, params)

    async def cancel_gtt(self, gtt_id: str) -> None:
        """Cancel / delete a GTT rule by id."""
        self._require_connected()
        await self._adapter.cancel_gtt(gtt_id)

    async def get_gtt(self, gtt_id: str) -> Gtt:
        """Fetch and normalize a single GTT rule."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_gtt(gtt_id)
        return self._adapter.transformer.to_gtt(raw["data"])

    async def get_gtts(self) -> list[Gtt]:
        """Fetch and normalize all GTT rules."""
        self._require_connected()
        raw: JsonDict = await self._adapter.get_gtts()
        data = raw.get("data") or []
        if isinstance(data, list):
            return [self._adapter.transformer.to_gtt(g) for g in data]
        return [self._adapter.transformer.to_gtt(data)]

    async def close_all_positions(self) -> tuple[list[str], list[str]]:
        """Place offsetting market orders for every open position.

        Returns:
            Tuple of (placed_order_ids, failed_symbols).
        """
        self._require_connected()
        raw: JsonDict = await self._adapter.get_positions()
        placed: list[str] = []
        failed: list[str] = []
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
                failed.append(str(pos_raw.get("tradingsymbol", "unknown")))
        return placed, failed
