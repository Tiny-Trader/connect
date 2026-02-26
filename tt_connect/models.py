from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from tt_connect.enums import Side, ProductType, OrderType, OrderStatus
from tt_connect.instruments import Instrument


class GttLeg(BaseModel):
    """One trigger+order leg of a GTT rule.

    Used in both request models (PlaceGttRequest, ModifyGttRequest) and
    the response model (Gtt).  Single-leg GTTs have one entry; OCO (two-leg)
    Zerodha GTTs have two entries — one per trigger price.
    """

    trigger_price: float
    price: float        # limit price for the order placed when triggered
    side: Side
    qty: int
    product: ProductType


class PlaceGttRequest(BaseModel):
    """Canonical input model for placing a GTT rule."""

    instrument: Instrument
    last_price: float   # current market price — required by Zerodha for validation
    legs: list[GttLeg]  # 1 leg = single trigger; 2 legs = OCO (Zerodha only)


class ModifyGttRequest(BaseModel):
    """Canonical input model for modifying an existing GTT rule."""

    gtt_id: str
    instrument: Instrument   # needed to resolve token/exchange for AngelOne
    last_price: float
    legs: list[GttLeg]


class Gtt(BaseModel):
    """Normalized GTT rule record returned by get_gtt / get_gtts."""

    model_config = ConfigDict(frozen=True)

    gtt_id: str
    status: str          # raw broker status string (differs per broker)
    symbol: str          # broker's own trading symbol
    exchange: str
    legs: list[GttLeg]   # 1 for single, 2 for OCO


class PlaceOrderRequest(BaseModel):
    """Canonical input model for placing an order."""

    instrument: Instrument
    side: Side
    qty: int
    order_type: OrderType
    product: ProductType
    price: float | None = None
    trigger_price: float | None = None


class ModifyOrderRequest(BaseModel):
    """Canonical input model for modifying an existing order."""

    order_id: str
    qty: int | None = None
    price: float | None = None
    trigger_price: float | None = None
    order_type: OrderType | None = None


class Profile(BaseModel):
    """Normalized broker account profile."""

    model_config = ConfigDict(frozen=True)

    client_id: str
    name: str
    email: str
    phone: str | None = None


class Fund(BaseModel):
    """Normalized funds/margin summary."""

    model_config = ConfigDict(frozen=True)

    available: float
    used: float
    total: float
    collateral: float = 0.0
    m2m_unrealized: float = 0.0
    m2m_realized: float = 0.0


class Holding(BaseModel):
    """Normalized demat holding record."""

    model_config = ConfigDict(frozen=True)

    instrument: Instrument
    qty: int
    avg_price: float
    ltp: float
    pnl: float
    pnl_percent: float = 0.0


class Position(BaseModel):
    """Normalized open position record."""

    model_config = ConfigDict(frozen=True)

    instrument: Instrument
    qty: int
    avg_price: float
    ltp: float
    pnl: float
    product: ProductType


class Order(BaseModel):
    """Normalized order record."""

    model_config = ConfigDict(frozen=True)

    id: str
    instrument: Instrument | None = None
    side: Side
    qty: int
    filled_qty: int
    product: ProductType
    order_type: OrderType
    status: OrderStatus
    price: float | None = None
    trigger_price: float | None = None
    avg_price: float | None = None
    timestamp: datetime | None = None


class Trade(BaseModel):
    """Normalized trade-book entry."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    instrument: Instrument
    side: Side
    qty: int
    avg_price: float
    trade_value: float
    product: ProductType
    timestamp: datetime | None = None


class Margin(BaseModel):
    """Normalized margin estimation result."""

    model_config = ConfigDict(frozen=True)

    total: float            # initial total margin required
    span: float
    exposure: float
    option_premium: float = 0.0
    final_total: float      # after portfolio netting / spread benefit
    benefit: float          # = total - final_total


class Tick(BaseModel):
    """Normalized streaming market data tick."""

    model_config = ConfigDict(frozen=True)

    instrument: Instrument
    ltp: float
    volume: int | None = None
    oi: int | None = None
    bid: float | None = None
    ask: float | None = None
    timestamp: datetime | None = None
