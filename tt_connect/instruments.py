from __future__ import annotations
from datetime import date
from pydantic import BaseModel, model_validator
from tt_connect.enums import Exchange, OptionType


class Instrument(BaseModel, frozen=True):
    """Canonical base instrument shape accepted by client APIs."""

    exchange: Exchange
    symbol: str


class Index(Instrument):
    """
    A market index (NIFTY 50, SENSEX, NIFTY BANK etc.).
    Not directly tradeable — used for LTP subscription and as
    the canonical underlying reference for index F&O.
    """
    exchange: Exchange


class Equity(Instrument):
    """Cash-market equity or ETF."""

    exchange: Exchange


class Future(Instrument):
    """Futures contract keyed by canonical underlying symbol + expiry."""

    expiry: date

    @model_validator(mode="after")
    def _validate(self) -> Future:
        """Placeholder for DB-backed validation after client initialization."""
        return self


class Option(Instrument):
    """Options contract keyed by underlying symbol, expiry, strike and side."""

    expiry: date
    strike: float
    option_type: OptionType

    @model_validator(mode="after")
    def _validate(self) -> Option:
        """Placeholder for DB-backed validation after client initialization."""
        return self


class Currency(Instrument):
    """Currency derivative instrument."""

    exchange: Exchange


class Commodity(Instrument):
    """Commodity derivative instrument."""

    exchange: Exchange
