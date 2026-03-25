"""Unit tests for GTT transformer methods — AngelOne and Zerodha."""

from __future__ import annotations

import json

import pytest

from tt_connect.brokers.angelone.transformer import AngelOneTransformer
from tt_connect.brokers.zerodha.transformer import ZerodhaTransformer
from tt_connect.core.models.enums import ProductType, Side
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import GttLeg, ModifyGttRequest, PlaceGttRequest
from tt_connect.core.exceptions import InvalidOrderError


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

INSTR = Equity(exchange="NSE", symbol="SBIN")

SINGLE_LEG = GttLeg(
    trigger_price=196.0,
    price=195.0,
    side=Side.BUY,
    qty=10,
    product=ProductType.CNC,
)

PLACE_REQ = PlaceGttRequest(
    instrument=INSTR,
    last_price=200.0,
    legs=[SINGLE_LEG],
)

MODIFY_REQ = ModifyGttRequest(
    gtt_id="42",
    instrument=INSTR,
    last_price=200.0,
    legs=[SINGLE_LEG],
)


# ---------------------------------------------------------------------------
# AngelOne transformer — GTT
# ---------------------------------------------------------------------------

class TestAngelOneGtt:
    TOKEN         = "3045"
    BROKER_SYMBOL = "SBIN-EQ"
    EXCHANGE      = "NSE"

    def test_to_gtt_params_single_leg(self) -> None:
        params = AngelOneTransformer.to_gtt_params(
            self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, PLACE_REQ
        )
        assert params["symboltoken"]     == self.TOKEN
        assert params["tradingsymbol"]   == self.BROKER_SYMBOL
        assert params["exchange"]        == self.EXCHANGE
        assert params["transactiontype"] == "BUY"
        assert params["producttype"]     == "DELIVERY"   # CNC → DELIVERY
        assert params["triggerprice"]    == "196.0"
        assert params["price"]           == "195.0"
        assert params["qty"]             == "10"

    def test_to_gtt_params_margin_product(self) -> None:
        leg = GttLeg(trigger_price=100.0, price=99.0, side=Side.SELL,
                     qty=5, product=ProductType.NRML)
        req = PlaceGttRequest(instrument=INSTR, last_price=105.0, legs=[leg])
        params = AngelOneTransformer.to_gtt_params(
            self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
        )
        assert params["producttype"] == "MARGIN"

    def test_to_modify_gtt_params(self) -> None:
        params = AngelOneTransformer.to_modify_gtt_params(
            self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, MODIFY_REQ
        )
        assert params["id"]           == "42"
        assert params["symboltoken"]  == self.TOKEN
        assert params["triggerprice"] == "196.0"
        assert params["price"]        == "195.0"
        assert params["qty"]          == "10"

    def test_to_gtt_id_extracts_id(self) -> None:
        raw = {"status": True, "data": {"id": "7"}}
        assert AngelOneTransformer.to_gtt_id(raw) == "7"

    def test_to_gtt_normalizes_record(self) -> None:
        raw = {
            "id":              "1",
            "status":          "NEW",
            "tradingsymbol":   "SBIN-EQ",
            "exchange":        "NSE",
            "transactiontype": "BUY",
            "producttype":     "DELIVERY",
            "price":           "195",
            "qty":             "10",
            "triggerprice":    "196",
        }
        gtt = AngelOneTransformer.to_gtt(raw)
        assert gtt.gtt_id   == "1"
        assert gtt.status   == "NEW"
        assert gtt.symbol   == "SBIN-EQ"
        assert gtt.exchange == "NSE"
        assert len(gtt.legs) == 1
        leg = gtt.legs[0]
        assert leg.trigger_price == pytest.approx(196.0)
        assert leg.price         == pytest.approx(195.0)
        assert leg.side          == Side.BUY
        assert leg.qty           == 10
        assert leg.product       == ProductType.CNC

    def test_to_gtt_margin_product(self) -> None:
        raw = {
            "id": "2", "status": "ACTIVE",
            "tradingsymbol": "INFY-EQ", "exchange": "NSE",
            "transactiontype": "SELL", "producttype": "MARGIN",
            "price": "1000", "qty": "5", "triggerprice": "1010",
        }
        gtt = AngelOneTransformer.to_gtt(raw)
        assert gtt.legs[0].product == ProductType.NRML

    def test_to_gtt_params_rejects_empty_legs(self) -> None:
        req = PlaceGttRequest(instrument=INSTR, last_price=200.0, legs=[])
        with pytest.raises(InvalidOrderError, match="exactly 1 leg"):
            AngelOneTransformer.to_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )

    def test_to_gtt_params_rejects_two_legs(self) -> None:
        leg2 = GttLeg(trigger_price=210.0, price=211.0, side=Side.SELL,
                      qty=10, product=ProductType.CNC)
        req = PlaceGttRequest(instrument=INSTR, last_price=200.0,
                              legs=[SINGLE_LEG, leg2])
        with pytest.raises(InvalidOrderError, match="exactly 1 leg"):
            AngelOneTransformer.to_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )

    def test_to_modify_gtt_params_rejects_empty_legs(self) -> None:
        req = ModifyGttRequest(gtt_id="42", instrument=INSTR,
                               last_price=200.0, legs=[])
        with pytest.raises(InvalidOrderError, match="exactly 1 leg"):
            AngelOneTransformer.to_modify_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )

    def test_to_modify_gtt_params_rejects_two_legs(self) -> None:
        leg2 = GttLeg(trigger_price=210.0, price=211.0, side=Side.SELL,
                      qty=10, product=ProductType.CNC)
        req = ModifyGttRequest(gtt_id="42", instrument=INSTR,
                               last_price=200.0, legs=[SINGLE_LEG, leg2])
        with pytest.raises(InvalidOrderError, match="exactly 1 leg"):
            AngelOneTransformer.to_modify_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )


# ---------------------------------------------------------------------------
# Zerodha transformer — GTT
# ---------------------------------------------------------------------------

class TestZerodhaGtt:
    TOKEN         = "256265"
    BROKER_SYMBOL = "INFY"
    EXCHANGE      = "NSE"

    def test_to_gtt_params_single(self) -> None:
        params = ZerodhaTransformer.to_gtt_params(
            self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, PLACE_REQ
        )
        assert params["type"] == "single"

        condition = json.loads(params["condition"])
        assert condition["exchange"]        == self.EXCHANGE
        assert condition["tradingsymbol"]   == self.BROKER_SYMBOL
        assert condition["trigger_values"]  == [196.0]
        assert condition["last_price"]      == 200.0

        orders = json.loads(params["orders"])
        assert len(orders) == 1
        assert orders[0]["transaction_type"] == "BUY"
        assert orders[0]["quantity"]         == 10
        assert orders[0]["product"]          == "CNC"
        assert orders[0]["price"]            == 195.0
        assert orders[0]["order_type"]       == "LIMIT"

    def test_to_gtt_params_two_leg(self) -> None:
        leg2 = GttLeg(
            trigger_price=210.0, price=211.0, side=Side.SELL,
            qty=10, product=ProductType.CNC
        )
        req = PlaceGttRequest(
            instrument=INSTR, last_price=205.0, legs=[SINGLE_LEG, leg2]
        )
        params = ZerodhaTransformer.to_gtt_params(
            self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
        )
        assert params["type"] == "two-leg"
        condition = json.loads(params["condition"])
        assert condition["trigger_values"] == [196.0, 210.0]
        orders = json.loads(params["orders"])
        assert len(orders) == 2

    def test_to_modify_gtt_params(self) -> None:
        params = ZerodhaTransformer.to_modify_gtt_params(
            self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, MODIFY_REQ
        )
        assert params["type"] == "single"
        condition = json.loads(params["condition"])
        assert condition["trigger_values"] == [196.0]

    def test_to_gtt_id(self) -> None:
        raw = {"status": "success", "data": {"trigger_id": 123}}
        assert ZerodhaTransformer.to_gtt_id(raw) == "123"

    def test_to_gtt_single(self) -> None:
        raw = {
            "id": 112127,
            "type": "single",
            "status": "active",
            "condition": {
                "exchange": "NSE",
                "tradingsymbol": "INFY",
                "trigger_values": [702.0],
                "last_price": 798.0,
            },
            "orders": [
                {
                    "exchange": "NSE",
                    "tradingsymbol": "INFY",
                    "product": "CNC",
                    "order_type": "LIMIT",
                    "transaction_type": "BUY",
                    "quantity": 1,
                    "price": 702.5,
                    "result": None,
                }
            ],
        }
        gtt = ZerodhaTransformer.to_gtt(raw)
        assert gtt.gtt_id   == "112127"
        assert gtt.status   == "active"
        assert gtt.symbol   == "INFY"
        assert gtt.exchange == "NSE"
        assert len(gtt.legs) == 1
        leg = gtt.legs[0]
        assert leg.trigger_price == pytest.approx(702.0)
        assert leg.price         == pytest.approx(702.5)
        assert leg.side          == Side.BUY
        assert leg.qty           == 1
        assert leg.product       == ProductType.CNC

    def test_to_gtt_two_leg(self) -> None:
        raw = {
            "id": 105099,
            "type": "two-leg",
            "status": "triggered",
            "condition": {
                "exchange": "NSE",
                "tradingsymbol": "RAIN",
                "trigger_values": [102.0, 103.7],
                "last_price": 102.6,
            },
            "orders": [
                {"transaction_type": "SELL", "quantity": 1, "price": 101.0,
                 "product": "CNC", "order_type": "LIMIT", "tradingsymbol": "RAIN",
                 "exchange": "NSE", "result": None},
                {"transaction_type": "SELL", "quantity": 1, "price": 104.0,
                 "product": "CNC", "order_type": "LIMIT", "tradingsymbol": "RAIN",
                 "exchange": "NSE", "result": None},
            ],
        }
        gtt = ZerodhaTransformer.to_gtt(raw)
        assert len(gtt.legs) == 2
        assert gtt.legs[0].trigger_price == pytest.approx(102.0)
        assert gtt.legs[1].trigger_price == pytest.approx(103.7)

    def test_to_gtt_empty_orders(self) -> None:
        """GTT with no orders list still produces a valid Gtt with empty legs."""
        raw = {
            "id": 999, "type": "single", "status": "expired",
            "condition": {"exchange": "NSE", "tradingsymbol": "X",
                          "trigger_values": [], "last_price": 100.0},
            "orders": [],
        }
        gtt = ZerodhaTransformer.to_gtt(raw)
        assert gtt.legs == []

    def test_to_gtt_params_rejects_empty_legs(self) -> None:
        req = PlaceGttRequest(instrument=INSTR, last_price=200.0, legs=[])
        with pytest.raises(InvalidOrderError, match="1 or 2 legs"):
            ZerodhaTransformer.to_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )

    def test_to_gtt_params_rejects_three_legs(self) -> None:
        legs = [SINGLE_LEG] * 3
        req = PlaceGttRequest(instrument=INSTR, last_price=200.0, legs=legs)
        with pytest.raises(InvalidOrderError, match="1 or 2 legs"):
            ZerodhaTransformer.to_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )

    def test_to_modify_gtt_params_rejects_empty_legs(self) -> None:
        req = ModifyGttRequest(gtt_id="42", instrument=INSTR,
                               last_price=200.0, legs=[])
        with pytest.raises(InvalidOrderError, match="1 or 2 legs"):
            ZerodhaTransformer.to_modify_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )

    def test_to_modify_gtt_params_rejects_three_legs(self) -> None:
        legs = [SINGLE_LEG] * 3
        req = ModifyGttRequest(gtt_id="42", instrument=INSTR,
                               last_price=200.0, legs=legs)
        with pytest.raises(InvalidOrderError, match="1 or 2 legs"):
            ZerodhaTransformer.to_modify_gtt_params(
                self.TOKEN, self.BROKER_SYMBOL, self.EXCHANGE, req
            )
