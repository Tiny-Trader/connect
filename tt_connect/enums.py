"""Canonical enums used across the public tt-connect API."""

from enum import StrEnum


class Exchange(StrEnum):
    """Supported exchanges/segments in canonical form."""

    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"   # NSE F&O
    BFO = "BFO"   # BSE F&O
    CDS = "CDS"   # Currency derivatives
    MCX = "MCX"   # Commodity


class OptionType(StrEnum):
    """Option side."""

    CE = "CE"
    PE = "PE"


class ProductType(StrEnum):
    """Broker product/margin categories."""

    CNC  = "CNC"   # Cash and carry (delivery)
    MIS  = "MIS"   # Margin intraday
    NRML = "NRML"  # Normal (F&O carry forward)


class OrderType(StrEnum):
    """Supported order execution types."""

    MARKET = "MARKET"
    LIMIT  = "LIMIT"
    SL     = "SL"    # Stop-loss limit
    SL_M   = "SL_M"  # Stop-loss market


class Side(StrEnum):
    """Order direction."""

    BUY  = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    """Normalized order lifecycle statuses."""

    PENDING   = "PENDING"
    OPEN      = "OPEN"
    COMPLETE  = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED  = "REJECTED"


class OnStale(StrEnum):
    """Behavior when local instrument data is stale."""

    FAIL = "fail"
    WARN = "warn"


class AuthMode(StrEnum):
    """Authentication strategy selection."""

    MANUAL = "manual"   # User supplies access_token; library never logs in autonomously
    AUTO   = "auto"     # Library performs TOTP login + token refresh automatically
