from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from tt_connect.core.exceptions import ConfigurationError
from tt_connect.core.models.enums import Exchange, OptionType

_CONSTRUCTION_EXAMPLES: dict[str, str] = {
    "Instrument": 'Instrument(exchange=Exchange.NSE, symbol="RELIANCE")',
    "Index": 'Index(exchange=Exchange.NSE, symbol="NIFTY")',
    "Equity": 'Equity(exchange=Exchange.NSE, symbol="RELIANCE")',
    "Future": (
        'Future(exchange=Exchange.NFO, symbol="NIFTY", expiry=date(2026, 3, 27))'
    ),
    "Option": (
        'Option(exchange=Exchange.NFO, symbol="NIFTY", expiry=date(2026, 3, 27), '
        "strike=25000, option_type=OptionType.CE)"
    ),
    "Currency": 'Currency(exchange=Exchange.CDS, symbol="USDINR")',
    "Commodity": 'Commodity(exchange=Exchange.MCX, symbol="GOLD")',
}


def _join_field_names(fields: list[str]) -> str:
    if len(fields) == 1:
        return fields[0]
    if len(fields) == 2:
        return f"{fields[0]} and {fields[1]}"
    return ", ".join(fields[:-1]) + f", and {fields[-1]}"


def _instrument_construction_error(cls: type[Any], exc: ValidationError) -> str:
    """Build a short, example-backed construction error for public instrument types."""
    name = cls.__name__
    example = _CONSTRUCTION_EXAMPLES.get(
        name, f'{name}(exchange=Exchange.NSE, symbol="SYMBOL")'
    )
    missing = [
        str(err["loc"][0])
        for err in exc.errors()
        if err["type"] == "missing" and err.get("loc")
    ]
    if missing:
        return (
            f"{name} requires {_join_field_names(missing)}.\n"
            f"  Example: {example}"
        )
    details = "; ".join(
        f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
        for err in exc.errors()
    )
    return f"Invalid {name}: {details}\n  Example: {example}"


class Instrument(BaseModel):
    """Canonical base instrument shape accepted by client APIs.

    Example::

        Instrument(exchange=Exchange.NSE, symbol="RELIANCE")
    """

    model_config = ConfigDict(frozen=True)
    exchange: Exchange
    symbol: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        try:
            super().__init__(*args, **kwargs)
        except ValidationError as exc:
            raise ConfigurationError(
                _instrument_construction_error(type(self), exc)
            ) from None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.exchange}:{self.symbol})"


class Index(Instrument):
    """A market index (NIFTY 50, SENSEX, NIFTY BANK etc.).

    Not directly tradeable — used for LTP subscription and as the canonical
    underlying reference for index F&O.

    Example::

        Index(exchange=Exchange.NSE, symbol="NIFTY")
    """

    exchange: Exchange


class Equity(Instrument):
    """Cash-market equity or ETF.

    Example::

        Equity(exchange=Exchange.NSE, symbol="RELIANCE")
    """

    exchange: Exchange


class Future(Instrument):
    """Futures contract keyed by canonical underlying symbol + expiry.

    Validity (does this expiry exist?) is checked at resolve time by
    ``InstrumentResolver``, not at construction.

    Example::

        Future(exchange=Exchange.NFO, symbol="NIFTY", expiry=date(2026, 3, 27))
    """

    expiry: date

    def __repr__(self) -> str:
        return f"Future({self.exchange}:{self.symbol} {self.expiry.isoformat()})"


class Option(Instrument):
    """Options contract keyed by underlying symbol, expiry, strike and side.

    Validity (does this contract exist?) is checked at resolve time by
    ``InstrumentResolver``, not at construction.

    Example::

        Option(
            exchange=Exchange.NFO,
            symbol="NIFTY",
            expiry=date(2026, 3, 27),
            strike=25000,
            option_type=OptionType.CE,
        )
    """

    expiry: date
    strike: float
    option_type: OptionType

    def __repr__(self) -> str:
        strike: float | int = (
            int(self.strike) if self.strike == int(self.strike) else self.strike
        )
        return (
            f"Option({self.exchange}:{self.symbol} {strike} "
            f"{self.option_type} {self.expiry.isoformat()})"
        )


class Currency(Instrument):
    """Currency derivative instrument.

    Example::

        Currency(exchange=Exchange.CDS, symbol="USDINR")
    """

    exchange: Exchange


class Commodity(Instrument):
    """Commodity derivative instrument.

    Example::

        Commodity(exchange=Exchange.MCX, symbol="GOLD")
    """

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
