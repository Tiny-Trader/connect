"""Public package entrypoint for tt-connect clients."""

import logging

from tt_connect.client import AsyncTTConnect
from tt_connect.config import AngelOneConfig, ZerodhaConfig
from tt_connect.enums import CandleInterval
from tt_connect.exceptions import ConfigurationError
from tt_connect.instruments import Equity, Future, Index, Option
from tt_connect.logging_utils import setup_logging
from tt_connect.models import (
    Candle,
    GetHistoricalRequest,
    Gtt,
    GttLeg,
    ModifyGttRequest,
    ModifyOrderRequest,
    PlaceGttRequest,
    PlaceOrderRequest,
    Tick,
)
from tt_connect.sync_client import TTConnect

# Import adapters to trigger auto-registration
import tt_connect.adapters.zerodha.adapter   # noqa: F401
import tt_connect.adapters.angelone.adapter  # noqa: F401

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "TTConnect",
    "AsyncTTConnect",
    # Config
    "AngelOneConfig",
    "ZerodhaConfig",
    "ConfigurationError",
    # Order models
    "PlaceOrderRequest",
    "ModifyOrderRequest",
    # GTT models
    "PlaceGttRequest",
    "ModifyGttRequest",
    "GttLeg",
    "Gtt",
    # Historical
    "GetHistoricalRequest",
    "Candle",
    "CandleInterval",
    # Quotes
    "Tick",
    # Instruments
    "Equity",
    "Future",
    "Index",
    "Option",
    # Logging
    "setup_logging",
]
