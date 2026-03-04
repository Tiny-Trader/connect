"""Unit tests for order idempotency key behaviour."""

from __future__ import annotations

from typing import Any

from tt_connect.brokers.angelone.transformer import AngelOneTransformer
from tt_connect.brokers.zerodha.transformer import ZerodhaTransformer
from tt_connect.core.models.enums import OrderType, ProductType, Side
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import PlaceOrderRequest

INSTR = Equity(exchange="NSE", symbol="RELIANCE")


def _req(**kwargs: Any) -> PlaceOrderRequest:
    defaults = dict(
        instrument=INSTR,
        side=Side.BUY,
        qty=1,
        order_type=OrderType.MARKET,
        product=ProductType.CNC,
    )
    return PlaceOrderRequest(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Auto-generation
# ---------------------------------------------------------------------------


def test_tag_auto_generated() -> None:
    req = _req()
    assert req.tag
    assert len(req.tag) == 36  # full UUID4 with dashes


def test_each_request_gets_unique_key() -> None:
    keys = {_req().tag for _ in range(20)}
    assert len(keys) == 20


def test_user_can_set_explicit_key() -> None:
    req = _req(tag="my-order-001")
    assert req.tag == "my-order-001"


# ---------------------------------------------------------------------------
# Zerodha — tag field
# ---------------------------------------------------------------------------


def test_zerodha_tag_included_in_params() -> None:
    req = _req()
    params = ZerodhaTransformer.to_order_params("2885", "RELIANCE", "NSE", req)
    assert "tag" in params


def test_zerodha_tag_max_20_chars() -> None:
    req = _req()
    params = ZerodhaTransformer.to_order_params("2885", "RELIANCE", "NSE", req)
    assert len(params["tag"]) <= 20


def test_zerodha_tag_alphanumeric_only() -> None:
    req = _req()
    params = ZerodhaTransformer.to_order_params("2885", "RELIANCE", "NSE", req)
    assert params["tag"].isalnum()


def test_zerodha_explicit_key_used_as_tag() -> None:
    req = _req(tag="abc-123-xyz-456-def")
    params = ZerodhaTransformer.to_order_params("2885", "RELIANCE", "NSE", req)
    # dashes stripped, truncated to 20
    assert params["tag"] == "abc123xyz456def"


def test_zerodha_same_request_same_tag_on_retry() -> None:
    """Same PlaceOrderRequest produces identical tag on repeated calls (retry-safe)."""
    req = _req()
    p1 = ZerodhaTransformer.to_order_params("2885", "RELIANCE", "NSE", req)
    p2 = ZerodhaTransformer.to_order_params("2885", "RELIANCE", "NSE", req)
    assert p1["tag"] == p2["tag"]


# ---------------------------------------------------------------------------
# AngelOne — uniqueorderid field
# ---------------------------------------------------------------------------


def test_angelone_uniqueorderid_included_in_params() -> None:
    req = _req()
    params = AngelOneTransformer.to_order_params("2885", "RELIANCE-EQ", "NSE", req)
    assert "uniqueorderid" in params


def test_angelone_uniqueorderid_matches_key() -> None:
    req = _req(tag="fixed-key-for-test")
    params = AngelOneTransformer.to_order_params("2885", "RELIANCE-EQ", "NSE", req)
    assert params["uniqueorderid"] == "fixed-key-for-test"


def test_angelone_same_request_same_id_on_retry() -> None:
    req = _req()
    p1 = AngelOneTransformer.to_order_params("2885", "RELIANCE-EQ", "NSE", req)
    p2 = AngelOneTransformer.to_order_params("2885", "RELIANCE-EQ", "NSE", req)
    assert p1["uniqueorderid"] == p2["uniqueorderid"]
