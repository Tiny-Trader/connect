"""Public package entrypoint for tt-connect clients."""

import logging

from tt_connect.core.client import AsyncTTConnect, TTConnect
from tt_connect.core.exceptions import ConfigurationError
from tt_connect.core.logging import setup_logging
from tt_connect.core.models import (
    # Enums
    CandleInterval,
    # Instruments
    Equity,
    Future,
    Index,
    Option,
    # Requests
    GetHistoricalRequest,
    GttLeg,
    ModifyGttRequest,
    ModifyOrderRequest,
    PlaceGttRequest,
    PlaceOrderRequest,
    # Responses
    Candle,
    Gtt,
    Tick,
)

# Auto-discover and register all broker packages (adapters + configs)
import tt_connect.brokers  # noqa: F401

# Re-export broker configs for user convenience
from tt_connect.brokers.zerodha.config import ZerodhaConfig
from tt_connect.brokers.angelone.config import AngelOneConfig

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
