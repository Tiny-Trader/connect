from enum import StrEnum


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"   # NSE F&O
    BFO = "BFO"   # BSE F&O
    CDS = "CDS"   # Currency derivatives
    MCX = "MCX"   # Commodity


class OptionType(StrEnum):
    CE = "CE"
    PE = "PE"


class ProductType(StrEnum):
    CNC  = "CNC"   # Cash and carry (delivery)
    MIS  = "MIS"   # Margin intraday
    NRML = "NRML"  # Normal (F&O carry forward)


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT  = "LIMIT"
    SL     = "SL"    # Stop-loss limit
    SL_M   = "SL_M"  # Stop-loss market


class Side(StrEnum):
    BUY  = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    PENDING   = "PENDING"
    OPEN      = "OPEN"
    COMPLETE  = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED  = "REJECTED"


class OnStale(StrEnum):
    FAIL = "fail"
    WARN = "warn"


class AuthMode(StrEnum):
    MANUAL = "manual"   # User supplies access_token; library never logs in autonomously
    AUTO   = "auto"     # Library performs TOTP login + token refresh automatically
