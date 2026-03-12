from __future__ import annotations
from dataclasses import dataclass
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


@dataclass(frozen=True)
class InstrumentInfo:
    """Metadata for any instrument row from the local DB."""

    instrument: Instrument
    name: str | None
    lot_size: int
    tick_size: float
    segment: str


@dataclass(frozen=True)
class OptionChainEntry:
    """CE/PE pair at a single strike."""

    strike: float
    ce: Option | None
    pe: Option | None


@dataclass
class OptionChain:
    """All strikes for one underlying + expiry combination.

    Entries are sorted by strike ascending. Use atm() and strikes_around()
    for convenience; or iterate entries directly for custom logic.
    """

    underlying: Instrument
    expiry: date
    entries: list[OptionChainEntry]  # sorted by strike asc

    def atm(self, spot: float) -> OptionChainEntry:
        """Entry with strike closest to spot price.

        Raises:
            ValueError: if the option chain has no entries.
        """
        if not self.entries:
            raise ValueError("atm(): no option entries available")
        return min(self.entries, key=lambda e: abs(e.strike - spot))

    def strikes_around(self, spot: float, n: int) -> list[OptionChainEntry]:
        """n entries centered on the ATM strike."""
        atm_entry = self.atm(spot)
        atm_idx = self.entries.index(atm_entry)
        half = n // 2
        start = max(0, atm_idx - half)
        end = min(len(self.entries), start + n)
        start = max(0, end - n)
        return self.entries[start:end]
