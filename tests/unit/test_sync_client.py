"""Unit tests for TTConnect synchronous wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tt_connect.core.models.enums import OrderStatus, OrderType, ProductType, Side
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import (
    Fund,
    Gtt,
    GttLeg,
    Holding,
    ModifyGttRequest,
    ModifyOrderRequest,
    Order,
    PlaceGttRequest,
    PlaceOrderRequest,
    Position,
    Profile,
    Trade,
)
from tt_connect.core.client._sync import TTConnect


# ---------------------------------------------------------------------------
# Shared instances
# ---------------------------------------------------------------------------

INSTR = Equity(exchange="NSE", symbol="RELIANCE")

PROFILE   = Profile(client_id="ZZ001", name="Test", email="t@t.com")
FUND      = Fund(available=10000.0, used=0.0, total=10000.0)
HOLDING   = Holding(instrument=INSTR, qty=10, avg_price=2800.0, ltp=2900.0, pnl=1000.0)
POSITION  = Position(instrument=INSTR, qty=50, avg_price=2800.0, ltp=2900.0,
                     pnl=5000.0, product=ProductType.MIS)
TRADE     = Trade(order_id="T1", instrument=INSTR, side=Side.BUY, qty=10,
                  avg_price=2800.0, trade_value=28000.0, product=ProductType.CNC,
                  timestamp=None)
ORDER     = Order(id="O1", side=Side.BUY, qty=10, filled_qty=0,
                  product=ProductType.CNC, order_type=OrderType.MARKET,
                  status=OrderStatus.OPEN)
GTT       = Gtt(gtt_id="G1", status="active", symbol="RELIANCE", exchange="NSE", legs=[])


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def client_and_mock():
    """TTConnect backed by a fully mocked AsyncTTConnect."""
    with patch("tt_connect.core.client._async.AsyncTTConnect") as mock_cls:
        mock_async = MagicMock()
        mock_async.init             = AsyncMock(return_value=None)
        mock_async.close            = AsyncMock(return_value=None)
        mock_async.get_profile      = AsyncMock(return_value=PROFILE)
        mock_async.get_funds        = AsyncMock(return_value=FUND)
        mock_async.get_holdings     = AsyncMock(return_value=[HOLDING])
        mock_async.get_positions    = AsyncMock(return_value=[POSITION])
        mock_async.get_trades       = AsyncMock(return_value=[TRADE])
        mock_async.place_order      = AsyncMock(return_value="O1")
        mock_async.modify_order     = AsyncMock(return_value=None)
        mock_async.cancel_order     = AsyncMock(return_value=None)
        mock_async.cancel_all_orders = AsyncMock(return_value=(["O1"], []))
        mock_async.close_all_positions = AsyncMock(return_value=(["C1"], []))
        mock_async.get_order        = AsyncMock(return_value=ORDER)
        mock_async.get_orders       = AsyncMock(return_value=[ORDER])
        mock_async.place_gtt        = AsyncMock(return_value="G1")
        mock_async.modify_gtt       = AsyncMock(return_value=None)
        mock_async.cancel_gtt       = AsyncMock(return_value=None)
        mock_async.get_gtt          = AsyncMock(return_value=GTT)
        mock_async.get_gtts         = AsyncMock(return_value=[GTT])
        mock_cls.return_value = mock_async

        client = TTConnect("zerodha", {})
        yield client, mock_async
        client.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_init_calls_async_init(client_and_mock):
    _, mock_async = client_and_mock
    mock_async.init.assert_awaited_once()


def test_context_manager_calls_close():
    with patch("tt_connect.core.client._async.AsyncTTConnect") as mock_cls:
        mock_async = MagicMock()
        mock_async.init  = AsyncMock(return_value=None)
        mock_async.close = AsyncMock(return_value=None)
        mock_cls.return_value = mock_async

        with TTConnect("zerodha", {}) as client:
            assert client is not None

        mock_async.close.assert_awaited()


def test_init_failure_cleans_up_loop_and_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    stop_sentinel = object()

    fake_loop = MagicMock()
    fake_loop.stop = stop_sentinel

    fake_thread = MagicMock()

    mock_async = MagicMock()
    mock_async.init = AsyncMock(return_value=None)

    class InitBoom(RuntimeError):
        pass

    def fake_run(self: TTConnect, coro):
        coro.close()
        raise InitBoom("init failed")

    with (
        patch("asyncio.new_event_loop", return_value=fake_loop),
        patch("threading.Thread", return_value=fake_thread),
        patch("tt_connect.core.client._async.AsyncTTConnect", return_value=mock_async),
    ):
        monkeypatch.setattr(TTConnect, "_run", fake_run)

        with pytest.raises(InitBoom):
            TTConnect("zerodha", {})

    fake_thread.start.assert_called_once()
    fake_loop.call_soon_threadsafe.assert_called_once_with(stop_sentinel)
    fake_thread.join.assert_called_once()
    fake_loop.close.assert_called_once()


# ---------------------------------------------------------------------------
# Portfolio delegations
# ---------------------------------------------------------------------------


def test_get_profile(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_profile()
    assert result is PROFILE
    mock_async.get_profile.assert_awaited_once()


def test_get_funds(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_funds()
    assert result is FUND
    mock_async.get_funds.assert_awaited_once()


def test_get_holdings(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_holdings()
    assert result == [HOLDING]
    mock_async.get_holdings.assert_awaited_once()


def test_get_positions(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_positions()
    assert result == [POSITION]
    mock_async.get_positions.assert_awaited_once()


def test_get_trades(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_trades()
    assert result == [TRADE]
    mock_async.get_trades.assert_awaited_once()


# ---------------------------------------------------------------------------
# Order delegations
# ---------------------------------------------------------------------------


def test_place_order(client_and_mock):
    client, mock_async = client_and_mock
    req = PlaceOrderRequest(
        instrument=INSTR, side=Side.BUY, qty=10,
        order_type=OrderType.MARKET, product=ProductType.CNC,
    )
    result = client.place_order(req)
    assert result == "O1"
    mock_async.place_order.assert_awaited_once_with(req)


def test_modify_order(client_and_mock):
    client, mock_async = client_and_mock
    req = ModifyOrderRequest(order_id="O1", price=2900.0)
    client.modify_order(req)
    mock_async.modify_order.assert_awaited_once_with(req)


def test_cancel_order(client_and_mock):
    client, mock_async = client_and_mock
    client.cancel_order("O1")
    mock_async.cancel_order.assert_awaited_once_with("O1")


def test_cancel_all_orders(client_and_mock):
    client, mock_async = client_and_mock
    cancelled, failed = client.cancel_all_orders()
    assert cancelled == ["O1"]
    assert failed == []
    mock_async.cancel_all_orders.assert_awaited_once()


def test_close_all_positions(client_and_mock):
    client, mock_async = client_and_mock
    placed, failed = client.close_all_positions()
    assert placed == ["C1"]
    assert failed == []
    mock_async.close_all_positions.assert_awaited_once()


def test_get_order(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_order("O1")
    assert result is ORDER
    mock_async.get_order.assert_awaited_once_with("O1")


def test_get_orders(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_orders()
    assert result == [ORDER]
    mock_async.get_orders.assert_awaited_once()


# ---------------------------------------------------------------------------
# GTT delegations
# ---------------------------------------------------------------------------


def test_place_gtt(client_and_mock):
    client, mock_async = client_and_mock
    req = PlaceGttRequest(
        instrument=INSTR, last_price=2800.0,
        legs=[GttLeg(trigger_price=3000.0, price=3005.0, side=Side.SELL,
                     qty=10, product=ProductType.CNC)],
    )
    result = client.place_gtt(req)
    assert result == "G1"
    mock_async.place_gtt.assert_awaited_once_with(req)


def test_modify_gtt(client_and_mock):
    client, mock_async = client_and_mock
    req = ModifyGttRequest(
        gtt_id="G1", instrument=INSTR, last_price=2800.0,
        legs=[GttLeg(trigger_price=3100.0, price=3105.0, side=Side.SELL,
                     qty=10, product=ProductType.CNC)],
    )
    client.modify_gtt(req)
    mock_async.modify_gtt.assert_awaited_once_with(req)


def test_cancel_gtt(client_and_mock):
    client, mock_async = client_and_mock
    client.cancel_gtt("G1")
    mock_async.cancel_gtt.assert_awaited_once_with("G1")


def test_get_gtt(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_gtt("G1")
    assert result is GTT
    mock_async.get_gtt.assert_awaited_once_with("G1")


def test_get_gtts(client_and_mock):
    client, mock_async = client_and_mock
    result = client.get_gtts()
    assert result == [GTT]
    mock_async.get_gtts.assert_awaited_once()
