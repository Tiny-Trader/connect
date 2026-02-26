"""Unit tests for AngelOne transformer."""

import pytest
from tt_connect.adapters.angelone.transformer import AngelOneTransformer
from tt_connect.enums import Exchange, OrderStatus, OrderType
from tt_connect.models import ModifyOrderRequest


# ---------------------------------------------------------------------------
# to_position
# ---------------------------------------------------------------------------


def _pos_raw(**kwargs):
    """Return a minimal position row with defaults."""
    base = {
        "exchange":       "NSE",
        "tradingsymbol":  "SBIN-EQ",
        "producttype":    "CNC",
        "netqty":         "1",
        "totalbuyavgprice": "500.0",
        "totalsellavgprice": "0",
        "cfbuyavgprice":  "0",
        "cfsellavgprice": "0",
    }
    base.update(kwargs)
    return base


def test_to_position_long_uses_buy_avg():
    pos = AngelOneTransformer.to_position(_pos_raw(netqty="5", totalbuyavgprice="200.0"))
    assert pos.qty == 5
    assert pos.avg_price == pytest.approx(200.0)


def test_to_position_short_uses_sell_avg():
    raw = _pos_raw(netqty="-3", totalsellavgprice="300.0", totalbuyavgprice="0")
    pos = AngelOneTransformer.to_position(raw)
    assert pos.qty == -3
    assert pos.avg_price == pytest.approx(300.0)


def test_to_position_sell_avg_typo_fixed():
    """Regression: field was 'totalsellav gprice' (space) — now fixed."""
    raw = _pos_raw(netqty="-2", totalsellavgprice="450.0", cfsellavgprice="0")
    pos = AngelOneTransformer.to_position(raw)
    # With typo, avg would be 0; with fix it's 450.0
    assert pos.avg_price == pytest.approx(450.0)


def test_to_position_short_falls_back_to_cf_sell_avg():
    raw = _pos_raw(netqty="-1", totalsellavgprice="0", cfsellavgprice="350.0")
    pos = AngelOneTransformer.to_position(raw)
    assert pos.avg_price == pytest.approx(350.0)


def test_to_position_strips_eq_suffix():
    pos = AngelOneTransformer.to_position(_pos_raw(tradingsymbol="RELIANCE-EQ"))
    assert pos.instrument.symbol == "RELIANCE"


def test_to_position_exchange_mapped():
    pos = AngelOneTransformer.to_position(_pos_raw(exchange="NSE"))
    assert pos.instrument.exchange == Exchange.NSE


# ---------------------------------------------------------------------------
# to_modify_params
# ---------------------------------------------------------------------------


def test_to_modify_params_includes_variety_and_duration():
    req = ModifyOrderRequest(order_id="ORD001", price=150.0)
    params = AngelOneTransformer.to_modify_params(req)
    assert params["variety"]  == "NORMAL"
    assert params["duration"] == "DAY"
    assert params["orderid"]  == "ORD001"


def test_to_modify_params_optional_fields_only_when_set():
    req = ModifyOrderRequest(order_id="ORD002")
    params = AngelOneTransformer.to_modify_params(req)
    assert "quantity"     not in params
    assert "price"        not in params
    assert "triggerprice" not in params
    assert "ordertype"    not in params


def test_to_modify_params_all_fields():
    req = ModifyOrderRequest(
        order_id="ORD003",
        qty=10,
        price=200.0,
        trigger_price=195.0,
        order_type=OrderType.SL,
    )
    params = AngelOneTransformer.to_modify_params(req)
    assert params["quantity"]     == "10"
    assert params["price"]        == "200.0"
    assert params["triggerprice"] == "195.0"
    assert params["ordertype"]    == "SL"


# ---------------------------------------------------------------------------
# to_order
# ---------------------------------------------------------------------------


def _order_raw(**kwargs):
    base = {
        "orderid":         "O123",
        "status":          "open",
        "transactiontype": "BUY",
        "quantity":        "10",
        "filledshares":    "0",
        "producttype":     "CNC",
        "ordertype":       "LIMIT",
        "price":           "100.0",
        "updatetime":      "16-Jan-2024 10:00:00",
    }
    base.update(kwargs)
    return base


def test_to_order_status_modified_maps_to_open():
    o = AngelOneTransformer.to_order(_order_raw(status="modified"))
    assert o.status == OrderStatus.OPEN


def test_to_order_status_not_modified_maps_to_open():
    o = AngelOneTransformer.to_order(_order_raw(status="not modified"))
    assert o.status == OrderStatus.OPEN


def test_to_order_status_complete():
    o = AngelOneTransformer.to_order(_order_raw(status="complete"))
    assert o.status == OrderStatus.COMPLETE


def test_to_order_uses_filledshares():
    o = AngelOneTransformer.to_order(_order_raw(filledshares="5"))
    assert o.filled_qty == 5


# ---------------------------------------------------------------------------
# parse_error
# ---------------------------------------------------------------------------


def test_parse_error_authentication():
    from tt_connect.exceptions import AuthenticationError
    raw = {"errorcode": "AG8001", "message": "Invalid token"}
    err = AngelOneTransformer.parse_error(raw)
    assert isinstance(err, AuthenticationError)


def test_parse_error_order_error():
    from tt_connect.exceptions import OrderError
    raw = {"errorcode": "AB2002", "message": "ROBO blocked"}
    err = AngelOneTransformer.parse_error(raw)
    assert isinstance(err, OrderError)


def test_parse_error_unknown_code_becomes_broker_error():
    from tt_connect.exceptions import BrokerError
    raw = {"errorcode": "ZZZZ99", "message": "Unknown"}
    err = AngelOneTransformer.parse_error(raw)
    assert isinstance(err, BrokerError)
