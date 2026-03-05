from __future__ import annotations
from datetime import date
from pydantic import BaseModel, ConfigDict
from tt_connect.core.models.enums import Exchange, OptionType


class Instrument(BaseModel):
    """Canonical base instrument shape accepted by client APIs."""

    model_config = ConfigDict(frozen=True)
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
    """Futures contract keyed by canonical underlying symbol + expiry.

    Validity (does this expiry exist?) is checked at resolve time by
    ``InstrumentResolver``, not at construction.
    """

    expiry: date


class Option(Instrument):
    """Options contract keyed by underlying symbol, expiry, strike and side.

    Validity (does this contract exist?) is checked at resolve time by
    ``InstrumentResolver``, not at construction.
    """

    expiry: date
    strike: float
    option_type: OptionType


class Currency(Instrument):
    """Currency derivative instrument."""

    exchange: Exchange


class Commodity(Instrument):
    """Commodity derivative instrument."""

    exchange: Exchange
