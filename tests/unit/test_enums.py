import pytest
from tt_connect.core.models.enums import Exchange, OptionType, ProductType, OrderType, Side, OrderStatus, AuthMode

def test_exchange_values():
    assert Exchange.NSE == "NSE"
    assert Exchange.BSE == "BSE"
    assert Exchange.NFO == "NFO"

def test_option_type_values():
    assert OptionType.CE == "CE"
    assert OptionType.PE == "PE"

def test_product_type_values():
    assert ProductType.CNC == "CNC"
    assert ProductType.MIS == "MIS"
    assert ProductType.NRML == "NRML"

def test_order_type_values():
    assert OrderType.MARKET == "MARKET"
    assert OrderType.LIMIT == "LIMIT"

def test_side_values():
    assert Side.BUY == "BUY"
    assert Side.SELL == "SELL"

def test_order_status_values():
    assert OrderStatus.PENDING == "PENDING"
    assert OrderStatus.COMPLETE == "COMPLETE"

def test_auth_mode_values():
    assert AuthMode.MANUAL == "manual"
    assert AuthMode.AUTO == "auto"

def test_strenum_construction():
    assert Exchange("NSE") == Exchange.NSE
    with pytest.raises(ValueError):
        Exchange("INVALID")
