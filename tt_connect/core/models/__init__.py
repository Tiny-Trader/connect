"""Canonical data types for tt-connect."""

from tt_connect.core.models.config import BrokerConfig, validate_config
from tt_connect.core.models.enums import (
    AuthMode,
    CandleInterval,
    ClientState,
    Exchange,
    OnStale,
    OptionType,
    OrderStatus,
    OrderType,
    ProductType,
    Side,
)
from tt_connect.core.models.instruments import (
    Commodity,
    Currency,
    Equity,
    Future,
    Index,
    Instrument,
    Option,
)
from tt_connect.core.models.requests import (
    GetHistoricalRequest,
    GttLeg,
    ModifyGttRequest,
    ModifyOrderRequest,
    PlaceGttRequest,
    PlaceOrderRequest,
)
from tt_connect.core.models.responses import (
    Candle,
    Fund,
    Gtt,
    Holding,
    Margin,
    Order,
    Position,
    Profile,
    Tick,
    Trade,
)

__all__ = [
    # Config
    "BrokerConfig",
    "validate_config",
    # Enums
    "AuthMode",
    "CandleInterval",
    "ClientState",
    "Exchange",
    "OnStale",
    "OptionType",
    "OrderStatus",
    "OrderType",
    "ProductType",
    "Side",
    # Instruments
    "Commodity",
    "Currency",
    "Equity",
    "Future",
    "Index",
    "Instrument",
    "Option",
    # Requests
    "GetHistoricalRequest",
    "GttLeg",
    "ModifyGttRequest",
    "ModifyOrderRequest",
    "PlaceGttRequest",
    "PlaceOrderRequest",
    # Responses
    "Candle",
    "Fund",
    "Gtt",
    "Holding",
    "Margin",
    "Order",
    "Position",
    "Profile",
    "Tick",
    "Trade",
]
