import pytest

# All tests in this module share one event loop so the module-scoped broker
# fixture (and its httpx client) are always on the same loop as the test.
pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.live
async def test_profile_returns_real_client_id(angelone_broker):
    profile = await angelone_broker.get_profile()
    assert profile.client_id
    assert profile.name

@pytest.mark.live
async def test_funds_are_non_negative(angelone_broker):
    fund = await angelone_broker.get_funds()
    assert fund.available >= 0
    assert fund.total >= 0

@pytest.mark.live
async def test_get_holdings(angelone_broker):
    holdings = await angelone_broker.get_holdings()
    assert isinstance(holdings, list)

@pytest.mark.live
async def test_get_positions(angelone_broker):
    positions = await angelone_broker.get_positions()
    assert isinstance(positions, list)

@pytest.mark.live
async def test_get_orders(angelone_broker):
    orders = await angelone_broker.get_orders()
    assert isinstance(orders, list)
