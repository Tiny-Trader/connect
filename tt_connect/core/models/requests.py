"""Canonical request models — what users send to the broker."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from tt_connect.core.models.enums import CandleInterval, OrderType, ProductType, Side
from tt_connect.core.models.instruments import Instrument


class GttLeg(BaseModel):
    """One trigger+order leg of a GTT rule.

    Used in both request models (PlaceGttRequest, ModifyGttRequest) and
    the response model (Gtt).  Single-leg GTTs have one entry; OCO (two-leg)
    GTTs have two entries — one per trigger price.
    """

    trigger_price: float
    price: float        # limit price for the order placed when triggered
    side: Side
    qty: int
    product: ProductType


class PlaceGttRequest(BaseModel):
    """Canonical input model for placing a GTT rule."""

    instrument: Instrument
    last_price: float   # current market price — required by some brokers for validation
    legs: list[GttLeg]  # 1 leg = single trigger; 2 legs = OCO


class ModifyGttRequest(BaseModel):
    """Canonical input model for modifying an existing GTT rule."""

    gtt_id: str
    instrument: Instrument   # needed to resolve token/exchange
    last_price: float
    legs: list[GttLeg]


class PlaceOrderRequest(BaseModel):
    """Canonical input model for placing an order.

    Attributes:
        instrument: The instrument to trade (Equity, Future, Option).
        side: Buy or sell.
        qty: Number of shares/lots.
        order_type: MARKET, LIMIT, SL, or SL_M.
        product: CNC (delivery), MIS (intraday), or NRML (F&O carry).
        price: Limit price — required for LIMIT and SL orders, ignored for MARKET.
        trigger_price: Stop-loss trigger — required for SL and SL_M orders.
        tag: Client-side correlation ID for tracing an order from placement
            to the broker's order book. Auto-generated as a UUID if not
            provided. Sent as ``tag`` (Zerodha, max 20 chars) or
            ``uniqueorderid`` (AngelOne).
    """

    instrument: Instrument
    side: Side
    qty: int
    order_type: OrderType
    product: ProductType
    price: float | None = None
    trigger_price: float | None = None
    tag: str = Field(default_factory=lambda: str(uuid4()))


class ModifyOrderRequest(BaseModel):
    """Canonical input model for modifying an existing order."""

    order_id: str
    qty: int | None = None
    price: float | None = None
    trigger_price: float | None = None
    order_type: OrderType | None = None


class GetHistoricalRequest(BaseModel):
    """Canonical input model for requesting historical OHLC candles."""

    instrument: Instrument
    interval: CandleInterval
    from_date: datetime
    to_date: datetime
    include_oi: bool = True
