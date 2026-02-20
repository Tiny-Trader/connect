"""
Zerodha instrument CSV parser.

Owns all parsing and classification logic for Zerodha's master dump.
Returns a ParsedInstruments container that the InstrumentManager can
insert without knowing anything about Zerodha's CSV format.

Processing order matches insert order (FK constraint):
  1. indices  — underlyings must exist before futures/options reference them
  2. equities — stocks on NSE/BSE (instrument_type=EQ)
  3. futures  — NFO-FUT and BFO-FUT
  4. options  — (future chunk)
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date


# ---------------------------------------------------------------------------
# Canonical parsed types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParsedIndex:
    exchange: str
    symbol: str         # canonical — what users write in their code
    broker_symbol: str  # Zerodha's tradingsymbol
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str


@dataclass(frozen=True)
class ParsedEquity:
    exchange: str
    symbol: str         # canonical — same as broker_symbol for equities
    broker_symbol: str  # Zerodha's tradingsymbol
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str


@dataclass(frozen=True)
class ParsedFuture:
    exchange: str             # NFO or BFO (the derivative exchange, stored in DB)
    symbol: str               # underlying canonical name — e.g. "NIFTY", "RELIANCE"
    broker_symbol: str        # Zerodha's tradingsymbol — e.g. "NIFTY26FEBFUT"
    segment: str              # NFO-FUT or BFO-FUT
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    underlying_exchange: str  # NSE for NFO, BSE for BFO — used to resolve underlying_id


@dataclass(frozen=True)
class ParsedOption:
    exchange: str             # NFO or BFO (the derivative exchange, stored in DB)
    symbol: str               # underlying canonical name — e.g. "NIFTY", "RELIANCE"
    broker_symbol: str        # Zerodha's tradingsymbol — e.g. "NIFTY26FEB23000CE"
    segment: str              # NFO-OPT or BFO-OPT
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    strike: float
    option_type: str          # CE or PE
    underlying_exchange: str  # NSE for NFO, BSE for BFO — used to resolve underlying_id


@dataclass
class ParsedInstruments:
    indices:  list[ParsedIndex]  = field(default_factory=list)
    equities: list[ParsedEquity] = field(default_factory=list)
    futures:  list[ParsedFuture] = field(default_factory=list)
    options:  list[ParsedOption] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exchange/segment filters
# ---------------------------------------------------------------------------

# Exchanges in scope for v1 equity instruments
_EQUITY_EXCHANGES = {"NSE", "BSE"}

# Segments we classify as indices (within in-scope exchanges)
_INDEX_SEGMENTS = {"INDICES"}

# Instrument types we classify as equities
_EQUITY_INSTRUMENT_TYPES = {"EQ"}

# Exchanges in scope for v1 futures
_FUT_EXCHANGES = {"NFO", "BFO"}

# Maps derivative exchange → underlying exchange
_UNDERLYING_EXCHANGE = {"NFO": "NSE", "BFO": "BSE"}

# ---------------------------------------------------------------------------
# Index name map
#
# Zerodha's F&O rows carry a `name` field that identifies the underlying index.
# These names do NOT always match the tradingsymbol stored in the INDICES segment.
# This map translates canonical name → (exchange, broker tradingsymbol).
#
# All indices that appear as F&O underlyings must be listed here.
# ---------------------------------------------------------------------------

INDEX_NAME_MAP: dict[str, tuple[str, str]] = {
    # NSE indices
    "NIFTY":      ("NSE", "NIFTY 50"),
    "BANKNIFTY":  ("NSE", "NIFTY BANK"),
    "MIDCPNIFTY": ("NSE", "NIFTY MID SELECT"),
    "FINNIFTY":   ("NSE", "NIFTY FIN SERVICE"),
    "NIFTY500":   ("NSE", "NIFTY 500"),
    "NIFTYNXT50": ("NSE", "NIFTY NEXT 50"),
    # BSE indices
    "SENSEX":     ("BSE", "SENSEX"),
    "BANKEX":     ("BSE", "BANKEX"),
    "SENSEX50":   ("BSE", "SNSX50"),
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse(raw_csv: str) -> ParsedInstruments:
    """
    Parse Zerodha's raw CSV instrument dump into a ParsedInstruments container.
    Rows outside v1 scope are silently skipped.
    """
    result = ParsedInstruments()
    reader = csv.DictReader(io.StringIO(raw_csv))

    for row in reader:
        exchange        = row["exchange"]
        segment         = row["segment"]
        instrument_type = row["instrument_type"]

        if exchange in _EQUITY_EXCHANGES:
            if segment in _INDEX_SEGMENTS:
                result.indices.append(_parse_index(row))
            elif instrument_type in _EQUITY_INSTRUMENT_TYPES:
                result.equities.append(_parse_equity(row))
            continue

        if exchange in _FUT_EXCHANGES:
            if instrument_type == "FUT":
                result.futures.append(_parse_future(row))
            elif instrument_type in ("CE", "PE"):
                result.options.append(_parse_option(row))
            continue

        # MCX, CDS, NCO — out of v1 scope, skip

    return result


# ---------------------------------------------------------------------------
# Per-type parsers
# ---------------------------------------------------------------------------

# Reverse of INDEX_NAME_MAP: broker tradingsymbol → canonical symbol
# e.g. "NIFTY 50" → "NIFTY", "SNSX50" → "SENSEX50"
_BROKER_TO_CANONICAL: dict[str, str] = {v[1]: k for k, v in INDEX_NAME_MAP.items()}


def _parse_index(row: dict) -> ParsedIndex:
    broker_symbol = row["tradingsymbol"]
    canonical_symbol = _BROKER_TO_CANONICAL.get(broker_symbol, broker_symbol)

    return ParsedIndex(
        exchange      = row["exchange"],
        symbol        = canonical_symbol,
        broker_symbol = broker_symbol,
        segment       = row["segment"],
        name          = row["name"] or None,
        lot_size      = int(row["lot_size"]),
        tick_size     = float(row["tick_size"]),
        broker_token  = row["instrument_token"],
    )


def _parse_equity(row: dict) -> ParsedEquity:
    symbol = row["tradingsymbol"]

    return ParsedEquity(
        exchange      = row["exchange"],
        symbol        = symbol,
        broker_symbol = symbol,
        segment       = row["segment"],
        name          = row["name"] or None,
        lot_size      = int(row["lot_size"]),
        tick_size     = float(row["tick_size"]),
        broker_token  = row["instrument_token"],
    )


def _parse_future(row: dict) -> ParsedFuture:
    exchange = row["exchange"]

    return ParsedFuture(
        exchange             = exchange,
        symbol               = row["name"],          # already canonical for both index & equity underlyings
        broker_symbol        = row["tradingsymbol"],
        segment              = row["segment"],
        lot_size             = int(row["lot_size"]),
        tick_size            = float(row["tick_size"]),
        broker_token         = row["instrument_token"],
        expiry               = date.fromisoformat(row["expiry"]),
        underlying_exchange  = _UNDERLYING_EXCHANGE[exchange],
    )


def _parse_option(row: dict) -> ParsedOption:
    exchange = row["exchange"]

    return ParsedOption(
        exchange             = exchange,
        symbol               = row["name"],          # already canonical for both index & equity underlyings
        broker_symbol        = row["tradingsymbol"],
        segment              = row["segment"],
        lot_size             = int(row["lot_size"]),
        tick_size            = float(row["tick_size"]),
        broker_token         = row["instrument_token"],
        expiry               = date.fromisoformat(row["expiry"]),
        strike               = float(row["strike"]),
        option_type          = row["instrument_type"],
        underlying_exchange  = _UNDERLYING_EXCHANGE[exchange],
    )
