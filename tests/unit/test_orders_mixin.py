"""Unit tests for OrdersMixin — orders, GTT, cancel_all, close_all_positions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from tt_connect.core.models.enums import OrderStatus, OrderType, ProductType, Side
from tt_connect.core.store.resolver import ResolvedInstrument
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import (
    Gtt,
    GttLeg,
    ModifyGttRequest,
    ModifyOrderRequest,
    Order,
    PlaceGttRequest,
    PlaceOrderRequest,
    Position,
)
from tt_connect.core.client._orders import OrdersMixin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INSTR = Equity(exchange="NSE", symbol="RELIANCE")
RESOLVED = ResolvedInstrument(token="2885", broker_symbol="RELIANCE", exchange="NSE")


def _make_client() -> OrdersMixin:
    """OrdersMixin wired to a mock adapter — no real IO."""

    class _Fake(OrdersMixin):
        def _require_connected(self) -> None:
            pass

        async def _resolve(self, instrument):  # type: ignore[override]
            return RESOLVED

    client: _Fake = object.__new__(_Fake)
    client._adapter = MagicMock()
    # No resolver by default — token_from_order returns None so instrument stays None
    client._resolver = None  # type: ignore[assignment]
    return client


def _order(order_id: str = "O1", status: OrderStatus = OrderStatus.OPEN) -> Order:
    return Order(
        id=order_id,
        side=Side.BUY,
        qty=10,
        filled_qty=0,
        product=ProductType.CNC,
        order_type=OrderType.MARKET,
        status=status,
    )


# ---------------------------------------------------------------------------
# place_order
# ---------------------------------------------------------------------------


async def test_place_order_resolves_and_returns_id():
    client = _make_client()
    client._adapter.capabilities.verify = MagicMock()
    client._adapter.transformer.to_order_params.return_value = {"qty": 10}
    client._adapter.place_order = AsyncMock(return_value={"data": {"order_id": "O1"}})
    client._adapter.transformer.to_order_id.return_value = "O1"

    req = PlaceOrderRequest(
        instrument=INSTR, side=Side.BUY, qty=10,
        order_type=OrderType.MARKET, product=ProductType.CNC,
    )
    result = await client.place_order(req)

    assert result == "O1"
    client._adapter.capabilities.verify.assert_called_once_with(
        INSTR, OrderType.MARKET, ProductType.CNC
    )
    client._adapter.transformer.to_order_params.assert_called_once_with(
        RESOLVED.token, RESOLVED.broker_symbol, RESOLVED.exchange, req,
    )
    client._adapter.place_order.assert_awaited_once_with({"qty": 10})


async def test_place_order_limit_passes_price():
    client = _make_client()
    client._adapter.capabilities.verify = MagicMock()
    client._adapter.transformer.to_order_params.return_value = {"qty": 5, "price": 2900.0}
    client._adapter.place_order = AsyncMock(return_value={"data": {"order_id": "L1"}})
    client._adapter.transformer.to_order_id.return_value = "L1"

    req = PlaceOrderRequest(
        instrument=INSTR, side=Side.BUY, qty=5,
        order_type=OrderType.LIMIT, product=ProductType.MIS, price=2900.0,
    )
    result = await client.place_order(req)

    assert result == "L1"


# ---------------------------------------------------------------------------
# modify_order
# ---------------------------------------------------------------------------


async def test_modify_order_builds_params_and_calls_adapter():
    client = _make_client()
    client._adapter.transformer.to_modify_params.return_value = {"price": 1000.0}
    client._adapter.modify_order = AsyncMock(return_value={})

    req = ModifyOrderRequest(order_id="O1", price=1000.0)
    await client.modify_order(req)

    client._adapter.transformer.to_modify_params.assert_called_once_with(req)
    client._adapter.modify_order.assert_awaited_once_with("O1", {"price": 1000.0})


# ---------------------------------------------------------------------------
# cancel_order
# ---------------------------------------------------------------------------


async def test_cancel_order_delegates_to_adapter():
    client = _make_client()
    client._adapter.cancel_order = AsyncMock(return_value={})

    await client.cancel_order("O1")

    client._adapter.cancel_order.assert_awaited_once_with("O1")


# ---------------------------------------------------------------------------
# cancel_all_orders
# ---------------------------------------------------------------------------


async def test_cancel_all_orders_cancels_open_and_pending():
    client = _make_client()
    o_open    = _order("O1", OrderStatus.OPEN)
    o_pending = _order("O2", OrderStatus.PENDING)
    o_done    = _order("O3", OrderStatus.COMPLETE)

    client._adapter.get_orders = AsyncMock(return_value={"data": [{}, {}, {}]})
    client._adapter.transformer.to_order.side_effect = [o_open, o_pending, o_done]
    client._adapter.cancel_order = AsyncMock(return_value={})

    cancelled, failed = await client.cancel_all_orders()

    assert set(cancelled) == {"O1", "O2"}
    assert failed == []
    assert client._adapter.cancel_order.await_count == 2


async def test_cancel_all_orders_records_failures():
    client = _make_client()
    o1 = _order("O1", OrderStatus.OPEN)
    o2 = _order("O2", OrderStatus.OPEN)

    client._adapter.get_orders = AsyncMock(return_value={"data": [{}, {}]})
    client._adapter.transformer.to_order.side_effect = [o1, o2]

    async def _cancel(order_id: str) -> dict:
        if order_id == "O2":
            raise RuntimeError("broker rejected")
        return {}

    client._adapter.cancel_order = AsyncMock(side_effect=_cancel)

    cancelled, failed = await client.cancel_all_orders()

    assert cancelled == ["O1"]
    assert failed == ["O2"]


async def test_cancel_all_orders_no_open_returns_empty():
    client = _make_client()
    client._adapter.get_orders = AsyncMock(return_value={"data": [{}]})
    client._adapter.transformer.to_order.return_value = _order("O1", OrderStatus.COMPLETE)
    client._adapter.cancel_order = AsyncMock()

    cancelled, failed = await client.cancel_all_orders()

    assert cancelled == []
    assert failed == []
    client._adapter.cancel_order.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_order / get_orders
# ---------------------------------------------------------------------------


async def test_get_order_returns_normalized_order():
    client = _make_client()
    raw_data = {"order_id": "O1", "status": "COMPLETE"}
    client._adapter.get_order = AsyncMock(return_value={"data": raw_data})
    client._adapter.transformer.token_from_order.return_value = None  # no token → instrument=None
    expected = _order("O1", OrderStatus.COMPLETE)
    client._adapter.transformer.to_order.return_value = expected

    result = await client.get_order("O1")

    assert result is expected
    client._adapter.transformer.to_order.assert_called_once_with(raw_data, instrument=None)


async def test_get_order_populates_instrument_when_resolver_returns_one():
    client = _make_client()
    raw_data = {"order_id": "O1", "instrument_token": 2885}
    client._adapter.get_order = AsyncMock(return_value={"data": raw_data})
    client._adapter.transformer.token_from_order.return_value = "2885"
    mock_resolver = MagicMock()
    mock_resolver.reverse_resolve = AsyncMock(return_value=INSTR)
    client._resolver = mock_resolver  # type: ignore[assignment]
    expected = _order("O1")
    client._adapter.transformer.to_order.return_value = expected

    result = await client.get_order("O1")

    assert result is expected
    mock_resolver.reverse_resolve.assert_awaited_once_with("2885")
    client._adapter.transformer.to_order.assert_called_once_with(raw_data, instrument=INSTR)


async def test_get_orders_returns_all_orders():
    client = _make_client()
    o1, o2 = _order("O1"), _order("O2")
    client._adapter.get_orders = AsyncMock(return_value={"data": [{}, {}]})
    client._adapter.transformer.token_from_order.return_value = None
    client._adapter.transformer.to_order.side_effect = [o1, o2]

    result = await client.get_orders()

    assert result == [o1, o2]


async def test_get_orders_empty():
    client = _make_client()
    client._adapter.get_orders = AsyncMock(return_value={"data": []})

    result = await client.get_orders()

    assert result == []


# ---------------------------------------------------------------------------
# close_all_positions
# ---------------------------------------------------------------------------


async def test_close_all_positions_skips_flat_positions():
    client = _make_client()
    flat = Position(
        instrument=INSTR, qty=0, avg_price=1.0, ltp=1.0, pnl=0.0,
        product=ProductType.MIS,
    )
    client._adapter.get_positions = AsyncMock(return_value={"data": [{}]})
    client._adapter.transformer.to_position.return_value = flat
    client._adapter.place_order = AsyncMock()

    placed, failed = await client.close_all_positions()

    assert placed == []
    assert failed == []
    client._adapter.place_order.assert_not_awaited()


async def test_close_all_positions_sells_long_position():
    client = _make_client()
    pos = Position(
        instrument=INSTR, qty=50, avg_price=2800.0, ltp=2900.0,
        pnl=5000.0, product=ProductType.MIS,
    )
    client._adapter.get_positions = AsyncMock(return_value={"data": [{"tradingsymbol": "RELIANCE"}]})
    client._adapter.transformer.to_position.return_value = pos
    client._adapter.transformer.to_close_position_params.return_value = {"qty": 50}
    client._adapter.place_order = AsyncMock(return_value={"data": {"order_id": "C1"}})
    client._adapter.transformer.to_order_id.return_value = "C1"

    placed, failed = await client.close_all_positions()

    assert placed == ["C1"]
    assert failed == []
    # Verify SELL side for long (qty>0)
    args = client._adapter.transformer.to_close_position_params.call_args[0]
    assert args[1] == 50         # abs(qty)
    assert args[2] == Side.SELL


async def test_close_all_positions_buys_short_position():
    client = _make_client()
    pos = Position(
        instrument=INSTR, qty=-10, avg_price=2800.0, ltp=2900.0,
        pnl=-1000.0, product=ProductType.MIS,
    )
    client._adapter.get_positions = AsyncMock(return_value={"data": [{"tradingsymbol": "RELIANCE"}]})
    client._adapter.transformer.to_position.return_value = pos
    client._adapter.transformer.to_close_position_params.return_value = {}
    client._adapter.place_order = AsyncMock(return_value={"data": {}})
    client._adapter.transformer.to_order_id.return_value = "C2"

    placed, failed = await client.close_all_positions()

    # Verify BUY side for short (qty<0)
    args = client._adapter.transformer.to_close_position_params.call_args[0]
    assert args[1] == 10         # abs(qty)
    assert args[2] == Side.BUY


async def test_close_all_positions_records_failure():
    client = _make_client()
    pos = Position(
        instrument=INSTR, qty=10, avg_price=100.0, ltp=100.0,
        pnl=0.0, product=ProductType.MIS,
    )
    client._adapter.get_positions = AsyncMock(
        return_value={"data": [{"tradingsymbol": "RELIANCE"}]}
    )
    client._adapter.transformer.to_position.return_value = pos
    client._adapter.transformer.to_close_position_params.return_value = {}
    client._adapter.place_order = AsyncMock(side_effect=RuntimeError("rejected"))

    placed, failed = await client.close_all_positions()

    assert placed == []
    assert len(failed) == 1


# ---------------------------------------------------------------------------
# GTT — place_gtt
# ---------------------------------------------------------------------------


async def test_place_gtt_resolves_and_returns_id():
    client = _make_client()
    req = PlaceGttRequest(
        instrument=INSTR,
        last_price=2800.0,
        legs=[GttLeg(trigger_price=3000.0, price=3005.0, side=Side.SELL,
                     qty=10, product=ProductType.CNC)],
    )
    client._adapter.transformer.to_gtt_params.return_value = {"type": "single"}
    client._adapter.place_gtt = AsyncMock(return_value={"data": {"id": "99"}})
    client._adapter.transformer.to_gtt_id.return_value = "99"

    result = await client.place_gtt(req)

    assert result == "99"
    client._adapter.transformer.to_gtt_params.assert_called_once_with(
        RESOLVED.token, RESOLVED.broker_symbol, RESOLVED.exchange, req,
    )


# ---------------------------------------------------------------------------
# GTT — modify_gtt
# ---------------------------------------------------------------------------


async def test_modify_gtt_builds_params_and_calls_adapter():
    client = _make_client()
    req = ModifyGttRequest(
        gtt_id="42",
        instrument=INSTR,
        last_price=2800.0,
        legs=[GttLeg(trigger_price=3100.0, price=3105.0, side=Side.SELL,
                     qty=10, product=ProductType.CNC)],
    )
    client._adapter.transformer.to_modify_gtt_params.return_value = {"type": "single"}
    client._adapter.modify_gtt = AsyncMock(return_value={})

    await client.modify_gtt(req)

    client._adapter.modify_gtt.assert_awaited_once_with("42", {"type": "single"})
    client._adapter.transformer.to_modify_gtt_params.assert_called_once_with(
        RESOLVED.token, RESOLVED.broker_symbol, RESOLVED.exchange, req,
    )


# ---------------------------------------------------------------------------
# GTT — cancel_gtt
# ---------------------------------------------------------------------------


async def test_cancel_gtt_delegates_to_adapter():
    client = _make_client()
    client._adapter.cancel_gtt = AsyncMock(return_value={})

    await client.cancel_gtt("42")

    client._adapter.cancel_gtt.assert_awaited_once_with("42")


# ---------------------------------------------------------------------------
# GTT — get_gtt
# ---------------------------------------------------------------------------


async def test_get_gtt_returns_normalized():
    client = _make_client()
    raw_data = {"id": "42", "status": "active"}
    client._adapter.get_gtt = AsyncMock(return_value={"data": raw_data})
    expected = Gtt(gtt_id="42", status="active", symbol="RELIANCE", exchange="NSE", legs=[])
    client._adapter.transformer.to_gtt.return_value = expected

    result = await client.get_gtt("42")

    assert result is expected
    client._adapter.transformer.to_gtt.assert_called_once_with(raw_data)


# ---------------------------------------------------------------------------
# GTT — get_gtts (list, dict, and None data)
# ---------------------------------------------------------------------------


async def test_get_gtts_list_data():
    client = _make_client()
    g = Gtt(gtt_id="1", status="active", symbol="INFY", exchange="NSE", legs=[])
    client._adapter.get_gtts = AsyncMock(return_value={"data": [{}]})
    client._adapter.transformer.to_gtt.return_value = g

    result = await client.get_gtts()

    assert result == [g]


async def test_get_gtts_dict_data_wrapped_in_list():
    """AngelOne may return a single dict instead of a list."""
    client = _make_client()
    g = Gtt(gtt_id="1", status="active", symbol="INFY", exchange="NSE", legs=[])
    client._adapter.get_gtts = AsyncMock(return_value={"data": {"id": "1"}})
    client._adapter.transformer.to_gtt.return_value = g

    result = await client.get_gtts()

    assert result == [g]


async def test_get_gtts_null_data_returns_empty():
    client = _make_client()
    client._adapter.get_gtts = AsyncMock(return_value={"data": None})

    result = await client.get_gtts()

    assert result == []
    client._adapter.transformer.to_gtt.assert_not_called()


async def test_get_gtts_missing_data_key_returns_empty():
    client = _make_client()
    client._adapter.get_gtts = AsyncMock(return_value={})

    result = await client.get_gtts()

    assert result == []
