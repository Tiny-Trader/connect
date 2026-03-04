"""Unit tests for PortfolioMixin — all five portfolio methods, no IO."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from tt_connect.core.models.enums import ProductType, Side
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import Fund, Holding, Position, Profile, Trade
from tt_connect.core.client._portfolio import PortfolioMixin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INSTR = Equity(exchange="NSE", symbol="INFY")


def _make_client() -> PortfolioMixin:
    """PortfolioMixin wired to a mock adapter — no real IO."""

    class _Fake(PortfolioMixin):
        def _require_connected(self) -> None:
            pass

        async def _resolve(self, instrument):  # type: ignore[override]
            raise NotImplementedError

    client: _Fake = object.__new__(_Fake)
    client._adapter = MagicMock()
    return client


# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------


async def test_get_profile_calls_adapter_and_transforms():
    client = _make_client()
    raw = {"user_id": "ZZ001", "user_name": "Alice", "email": "a@b.com"}
    client._adapter.get_profile = AsyncMock(return_value={"data": raw})
    expected = Profile(client_id="ZZ001", name="Alice", email="a@b.com")
    client._adapter.transformer.to_profile.return_value = expected

    result = await client.get_profile()

    client._adapter.get_profile.assert_awaited_once()
    client._adapter.transformer.to_profile.assert_called_once_with(raw)
    assert result is expected


# ---------------------------------------------------------------------------
# get_funds
# ---------------------------------------------------------------------------


async def test_get_funds_calls_adapter_and_transforms():
    client = _make_client()
    raw = {"available": {"cash": 50000.0}, "utilised": {"debits": 5000.0}}
    client._adapter.get_funds = AsyncMock(return_value={"data": raw})
    expected = Fund(available=50000.0, used=5000.0, total=55000.0)
    client._adapter.transformer.to_fund.return_value = expected

    result = await client.get_funds()

    client._adapter.get_funds.assert_awaited_once()
    client._adapter.transformer.to_fund.assert_called_once_with(raw)
    assert result is expected


# ---------------------------------------------------------------------------
# get_holdings
# ---------------------------------------------------------------------------


async def test_get_holdings_returns_transformed_list():
    client = _make_client()
    raw_h = {"tradingsymbol": "INFY", "exchange": "NSE", "quantity": 10}
    client._adapter.get_holdings = AsyncMock(return_value={"data": [raw_h]})
    expected = Holding(instrument=INSTR, qty=10, avg_price=1500.0, ltp=1600.0, pnl=1000.0)
    client._adapter.transformer.to_holding.return_value = expected

    result = await client.get_holdings()

    assert result == [expected]
    client._adapter.transformer.to_holding.assert_called_once_with(raw_h)


async def test_get_holdings_empty_returns_empty_list():
    client = _make_client()
    client._adapter.get_holdings = AsyncMock(return_value={"data": []})

    result = await client.get_holdings()

    assert result == []
    client._adapter.transformer.to_holding.assert_not_called()


async def test_get_holdings_multiple_items():
    client = _make_client()
    raws = [{"tradingsymbol": "INFY"}, {"tradingsymbol": "SBIN"}]
    client._adapter.get_holdings = AsyncMock(return_value={"data": raws})
    h1 = Holding(instrument=INSTR, qty=5, avg_price=1500.0, ltp=1600.0, pnl=500.0)
    h2 = Holding(
        instrument=Equity(exchange="NSE", symbol="SBIN"),
        qty=10, avg_price=500.0, ltp=520.0, pnl=200.0,
    )
    client._adapter.transformer.to_holding.side_effect = [h1, h2]

    result = await client.get_holdings()

    assert result == [h1, h2]
    assert client._adapter.transformer.to_holding.call_count == 2


# ---------------------------------------------------------------------------
# get_positions
# ---------------------------------------------------------------------------


async def test_get_positions_returns_transformed_list():
    client = _make_client()
    raw_p = {"tradingsymbol": "NIFTY", "exchange": "NSE", "quantity": 50}
    client._adapter.get_positions = AsyncMock(return_value={"data": [raw_p]})
    expected = Position(
        instrument=INSTR, qty=50, avg_price=23000.0, ltp=23500.0,
        pnl=25000.0, product=ProductType.MIS,
    )
    client._adapter.transformer.to_position.return_value = expected

    result = await client.get_positions()

    assert result == [expected]
    client._adapter.transformer.to_position.assert_called_once_with(raw_p)


async def test_get_positions_empty_returns_empty_list():
    client = _make_client()
    client._adapter.get_positions = AsyncMock(return_value={"data": []})

    result = await client.get_positions()

    assert result == []
    client._adapter.transformer.to_position.assert_not_called()


# ---------------------------------------------------------------------------
# get_trades
# ---------------------------------------------------------------------------


async def test_get_trades_returns_transformed_list():
    client = _make_client()
    raw_t = {"order_id": "T1", "tradingsymbol": "SBIN"}
    client._adapter.get_trades = AsyncMock(return_value={"data": [raw_t]})
    expected = Trade(
        order_id="T1", instrument=INSTR, side=Side.BUY,
        qty=5, avg_price=500.0, trade_value=2500.0,
        product=ProductType.CNC, timestamp=None,
    )
    client._adapter.transformer.to_trade.return_value = expected

    result = await client.get_trades()

    assert result == [expected]
    client._adapter.transformer.to_trade.assert_called_once_with(raw_t)


async def test_get_trades_empty_returns_empty_list():
    client = _make_client()
    client._adapter.get_trades = AsyncMock(return_value={"data": []})

    result = await client.get_trades()

    assert result == []
    client._adapter.transformer.to_trade.assert_not_called()
