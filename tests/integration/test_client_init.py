import pytest
import respx
import httpx
from pathlib import Path
from tt_connect.client import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

@respx.mock
async def test_init_calls_login_and_instruments(zerodha_csv, tmp_path, monkeypatch):
    # Mock the instruments endpoint
    respx.get("https://api.kite.trade/instruments").mock(
        return_value=httpx.Response(200, text=zerodha_csv)
    )

    # Patch DB_PATH to use a temp directory
    test_db_dir = tmp_path
    import tt_connect.instrument_manager.db as db_module
    monkeypatch.setattr(db_module, "DB_DIR", test_db_dir)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })
    
    # Before init, resolver should be None
    assert broker._resolver is None
    
    await broker.init()
    
    # After init, resolver should be set
    assert broker._resolver is not None
    
    # Instruments endpoint was called exactly once
    assert respx.calls.call_count == 1
    
    await broker.close()

@respx.mock
@pytest.mark.parametrize("zerodha_response", ["profile"], indirect=True)
async def test_client_get_profile(zerodha_response, monkeypatch, tmp_path):
    respx.get("https://api.kite.trade/user/profile").mock(
        return_value=httpx.Response(200, json=zerodha_response)
    )
    
    import tt_connect.instrument_manager.db as db_module
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })
    
    import aiosqlite
    broker._instrument_manager._conn = await aiosqlite.connect(":memory:")
    
    profile = await broker.get_profile()
    assert profile.client_id == "ZZ0001"
    
    await broker.close()

@respx.mock
@pytest.mark.parametrize("zerodha_response", ["holdings"], indirect=True)
async def test_client_get_holdings(zerodha_response, monkeypatch, tmp_path):
    respx.get("https://api.kite.trade/portfolio/holdings").mock(
        return_value=httpx.Response(200, json=zerodha_response)
    )
    
    import tt_connect.instrument_manager.db as db_module
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })
    
    import aiosqlite
    broker._instrument_manager._conn = await aiosqlite.connect(":memory:")
    
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

    import tt_connect.instrument_manager.db as db_module
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    broker = AsyncTTConnect("zerodha", {
        "api_key": "testkey",
        "access_token": "testtoken",
    })
    
    # Use populated_db fixture directly
    broker._instrument_manager._conn = populated_db
    from tt_connect.instrument_manager.resolver import InstrumentResolver
    broker._resolver = InstrumentResolver(populated_db, "zerodha")
    
    order_id = await broker.place_order(
        instrument=Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        qty=1,
        side=Side.BUY,
        product=ProductType.CNC,
        order_type=OrderType.MARKET
    )
    
    assert order_id == "240221000000001"
    assert respx.calls.call_count == 1
    
    await broker.close()
