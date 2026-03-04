import pytest
from tt_connect.brokers.zerodha.transformer import ZerodhaTransformer
from tt_connect.core.models.enums import OrderStatus, Exchange, ProductType, Side

@pytest.mark.parametrize("zerodha_response", ["profile"], indirect=True)
def test_to_profile(zerodha_response):
    raw = zerodha_response["data"]
    p = ZerodhaTransformer.to_profile(raw)
    assert p.client_id == "ZZ0001"
    assert p.name == "Test User"
    assert p.email == "test@example.com"
    assert p.phone == "9999999999"

@pytest.mark.parametrize("zerodha_response", ["funds"], indirect=True)
def test_to_fund(zerodha_response):
    raw = zerodha_response["data"]
    f = ZerodhaTransformer.to_fund(raw)
    assert f.available == 10000.0
    assert f.used == 0.0
    assert f.total == 10000.0
    assert f.collateral == 0.0

def test_to_holding_computes_pnl_percent():
    raw = {
        "tradingsymbol": "SBIN",
        "exchange": "NSE",
        "quantity": 10,
        "average_price": 400.0,
        "last_price": 440.0,
        "pnl": 400.0
    }
    h = ZerodhaTransformer.to_holding(raw)
    assert h.pnl_percent == pytest.approx(10.0)
    assert h.instrument.symbol == "SBIN"
    assert h.instrument.exchange == Exchange.NSE

def test_to_holding_zero_avg_price_does_not_crash():
    raw = {
        "tradingsymbol": "SBIN",
        "exchange": "NSE",
        "quantity": 10,
        "average_price": 0.0,
        "last_price": 440.0,
        "pnl": 0.0
    }
    h = ZerodhaTransformer.to_holding(raw)
    assert h.pnl_percent == 0.0

def test_to_order_maps_trigger_pending_status():
    raw = {
        "order_id": "12345",
        "status": "TRIGGER PENDING",
        "transaction_type": "BUY",
        "quantity": 10,
        "filled_quantity": 0,
        "product": "CNC",
        "order_type": "LIMIT",
        "price": 100.0,
        "order_timestamp": "2026-02-21T10:00:00"
    }
    o = ZerodhaTransformer.to_order(raw)
    assert o.status == OrderStatus.PENDING
    assert o.side == Side.BUY

def test_to_trade_computes_trade_value():
    raw = {
        "order_id": "12345",
        "tradingsymbol": "SBIN",
        "exchange": "NSE",
        "transaction_type": "BUY",
        "quantity": 5,
        "average_price": 200.0,
        "product": "CNC",
        "fill_timestamp": "2026-02-21T10:05:00"
    }
    t = ZerodhaTransformer.to_trade(raw)
    assert t.trade_value == pytest.approx(1000.0)
    assert t.qty == 5

def test_to_position_maps_fields():
    raw = {
        "tradingsymbol": "NIFTY26FEBFUT",
        "exchange": "NFO",
        "quantity": 50,
        "average_price": 23100.0,
        "last_price": 23150.0,
        "pnl": 2500.0,
        "product": "NRML"
    }
    p = ZerodhaTransformer.to_position(raw)
    assert p.instrument.symbol == "NIFTY26FEBFUT"
    assert p.qty == 50
    assert p.pnl == pytest.approx(2500.0)
    assert p.product == ProductType.NRML

def test_to_margin_computes_benefit():
    raw = {
        "initial": {
            "total": 100000.0,
            "span": 80000.0,
            "exposure": 20000.0,
            "option_premium": 0.0
        },
        "final": {
            "total": 70000.0
        }
    }
    m = ZerodhaTransformer.to_margin(raw)
    assert m.total == pytest.approx(100000.0)
    assert m.final_total == pytest.approx(70000.0)
    assert m.benefit == pytest.approx(30000.0)

def test_parse_error():
    raw = {
        "status": "error",
        "error_type": "TokenException",
        "message": "Invalid token"
    }
    err = ZerodhaTransformer.parse_error(raw)
    from tt_connect.core.exceptions import AuthenticationError
    assert isinstance(err, AuthenticationError)
    assert str(err) == "Invalid token"


@pytest.mark.parametrize("error_type,expected_cls", [
    ("UserException",    "AuthenticationError"),
    ("MarginException",  "OrderError"),
    ("HoldingException", "OrderError"),
    ("DataException",    "BrokerError"),
    ("GeneralException", "BrokerError"),
])
def test_parse_error_all_documented_types(error_type, expected_cls):
    import tt_connect.core.exceptions as exc
    raw = {"error_type": error_type, "message": "err"}
    err = ZerodhaTransformer.parse_error(raw)
    assert isinstance(err, getattr(exc, expected_cls))


@pytest.mark.parametrize("status,expected", [
    ("MODIFIED",                  OrderStatus.OPEN),
    ("MODIFY VALIDATION PENDING", OrderStatus.OPEN),
    ("PUT ORDER REQ RECEIVED",    OrderStatus.PENDING),
])
def test_to_order_new_status_mappings(status, expected):
    raw = {
        "order_id": "99",
        "status": status,
        "transaction_type": "BUY",
        "quantity": 1,
        "filled_quantity": 0,
        "product": "CNC",
        "order_type": "LIMIT",
        "order_timestamp": "2024-01-15T10:00:00",
    }
    o = ZerodhaTransformer.to_order(raw)
    assert o.status == expected
