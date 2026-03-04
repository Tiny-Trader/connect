import pytest
import respx
import httpx
from tt_connect.core.client._async import AsyncTTConnect
from tt_connect.core.models.enums import ClientState, Exchange, Side, ProductType, OrderType
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import PlaceOrderRequest


async def _bootstrap_connected_state(broker) -> None:
    import aiosqlite

    broker._core._instrument_manager._conn = await aiosqlite.connect(":memory:")
    broker._core._state = ClientState.CONNECTED


@respx.mock
async def test_init_calls_login_and_instruments(zerodha_csv, tmp_path, monkeypatch):
    # Mock the instruments endpoint
    respx.get("https://api.kite.trade/instruments").mock(
        return_value=httpx.Response(200, text=zerodha_csv)
    )

    # Patch DB_PATH to use a temp directory
    test_db_dir = tmp_path
    import tt_connect.core.store.schema as db_module
    monkeypatch.setattr(db_module, "DB_DIR", test_db_dir)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })

    # Before init, resolver should be None and state should be CREATED
    assert broker._core._resolver is None
    assert broker._core._state == ClientState.CREATED

    await broker.init()

    # After init, resolver should be set and state should be CONNECTED
    assert broker._core._resolver is not None
    assert broker._core._state == ClientState.CONNECTED

    # Instruments endpoint was called exactly once
    assert respx.calls.call_count == 1

    await broker.close()
    assert broker._core._state == ClientState.CLOSED

@respx.mock
@pytest.mark.parametrize("zerodha_response", ["profile"], indirect=True)
async def test_client_get_profile(zerodha_response, monkeypatch, tmp_path):
    respx.get("https://api.kite.trade/user/profile").mock(
        return_value=httpx.Response(200, json=zerodha_response)
    )

    import tt_connect.core.store.schema as db_module
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })

    await _bootstrap_connected_state(broker)

    profile = await broker.get_profile()
    assert profile.client_id == "ZZ0001"

    await broker.close()

@respx.mock
@pytest.mark.parametrize("zerodha_response", ["holdings"], indirect=True)
async def test_client_get_holdings(zerodha_response, monkeypatch, tmp_path):
    respx.get("https://api.kite.trade/portfolio/holdings").mock(
        return_value=httpx.Response(200, json=zerodha_response)
    )

    import tt_connect.core.store.schema as db_module
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })

    await _bootstrap_connected_state(broker)

    holdings = await broker.get_holdings()
    assert len(holdings) == 1
    assert holdings[0].instrument.symbol == "SBIN"

    await broker.close()

@respx.mock
@pytest.mark.parametrize("zerodha_response", ["order_response"], indirect=True)
async def test_client_place_order(zerodha_response, populated_db, monkeypatch, tmp_path):
    # Mock order placement
    respx.post("https://api.kite.trade/orders/regular").mock(
        return_value=httpx.Response(200, json=zerodha_response)
    )

    import tt_connect.core.store.schema as db_module
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })

    # Use populated_db fixture directly
    broker._core._instrument_manager._conn = populated_db
    from tt_connect.core.store.resolver import InstrumentResolver
    broker._core._resolver = InstrumentResolver(populated_db, "zerodha")
    broker._core._state = ClientState.CONNECTED

    req = PlaceOrderRequest(
        instrument=Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        side=Side.BUY,
        qty=1,
        product=ProductType.CNC,
        order_type=OrderType.MARKET,
    )
    order_id = await broker.place_order(req)

    assert order_id == "240221000000001"
    assert respx.calls.call_count == 1

    await broker.close()
