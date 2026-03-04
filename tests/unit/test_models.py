import pytest
from pydantic import ValidationError
from tt_connect.core.models import Profile, Fund, Holding, Order, Margin
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.models.enums import Exchange, Side, ProductType, OrderType, OrderStatus

def test_profile_validation():
    p = Profile(client_id="ZZ0001", name="Test", email="test@ex.com")
    assert p.phone is None
    with pytest.raises(ValidationError):
        Profile(client_id="ZZ0001") # Missing name, email

def test_fund_defaults():
    f = Fund(available=100.0, used=20.0, total=120.0)
    assert f.collateral == 0.0
    assert f.m2m_unrealized == 0.0

def test_frozen_models():
    p = Profile(client_id="ZZ0001", name="Test", email="test@ex.com")
    with pytest.raises(Exception): # Pydantic frozen model raises on mutation
        p.name = "New Name"

def test_holding_validation():
    inst = Instrument(exchange=Exchange.NSE, symbol="SBIN")
    h = Holding(instrument=inst, qty=10, avg_price=400.0, ltp=440.0, pnl=400.0)
    assert h.pnl_percent == 0.0 # Default

def test_order_instrument_optional():
    o = Order(
        id="123", side=Side.BUY, qty=1, filled_qty=0, 
        product=ProductType.CNC, order_type=OrderType.MARKET, 
        status=OrderStatus.OPEN
    )
    assert o.instrument is None

def test_margin_benefit_calc():
    # ZerodhaTransformer.to_margin already does the benefit calculation, 
    # but the model just stores it.
    m = Margin(total=1000.0, span=800.0, exposure=200.0, final_total=700.0, benefit=300.0)
    assert m.benefit == 300.0
