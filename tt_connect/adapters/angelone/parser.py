"""
AngelOne instrument JSON parser.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ParsedIndex:
    exchange: str
    symbol: str
    broker_symbol: str
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str


@dataclass(frozen=True)
class ParsedEquity:
    exchange: str
    symbol: str
    broker_symbol: str
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str


@dataclass(frozen=True)
class ParsedFuture:
    exchange: str
    symbol: str
    broker_symbol: str
    segment: str
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    underlying_exchange: str


@dataclass(frozen=True)
class ParsedOption:
    exchange: str
    symbol: str
    broker_symbol: str
    segment: str
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    strike: float
    option_type: str
    underlying_exchange: str


@dataclass
class ParsedInstruments:
    indices:  list[ParsedIndex]  = field(default_factory=list)
    equities: list[ParsedEquity] = field(default_factory=list)
    futures:  list[ParsedFuture] = field(default_factory=list)
    options:  list[ParsedOption] = field(default_factory=list)


def parse(raw_data: list[dict]) -> ParsedInstruments:
    """
    Parse AngelOne's instrument list (usually JSON) into a ParsedInstruments container.
    """
    result = ParsedInstruments()
    # TODO: Implement AngelOne specific parsing logic
    return result
