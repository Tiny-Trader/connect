import pytest

# All tests in this module share one event loop so the module-scoped broker
# fixture (and its httpx client) are always on the same loop as the test.
pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.live
async def test_profile_returns_real_client_id(angelone_broker) -> None:
    profile = await angelone_broker.get_profile()
    assert profile.client_id
    assert profile.name

@pytest.mark.live
async def test_funds_are_non_negative(angelone_broker) -> None:
    fund = await angelone_broker.get_funds()
    assert fund.available >= 0
    assert fund.total >= 0

@pytest.mark.live
async def test_get_holdings(angelone_broker) -> None:
    holdings = await angelone_broker.get_holdings()
    assert isinstance(holdings, list)

@pytest.mark.live
async def test_get_positions(angelone_broker) -> None:
    positions = await angelone_broker.get_positions()
    assert isinstance(positions, list)

@pytest.mark.live
async def test_get_orders(angelone_broker) -> None:
    orders = await angelone_broker.get_orders()
    assert isinstance(orders, list)


@pytest.mark.live
async def test_get_historical_returns_candles(angelone_broker) -> None:
    from datetime import datetime
    from tt_connect.enums import CandleInterval
    from tt_connect.instruments import Equity

    instr = Equity(exchange="NSE", symbol="SBIN")
    candles = await angelone_broker.get_historical(
        instr,
        CandleInterval.DAY,
        from_date=datetime(2025, 1, 1),
        to_date=datetime(2025, 1, 31),
    )
    assert isinstance(candles, list)
    assert len(candles) > 0
    c = candles[0]
    assert c.open > 0
    assert c.high >= c.low
    assert c.volume >= 0
