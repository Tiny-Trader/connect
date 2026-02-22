"""
AngelOne instrument JSON parser.

Owns all parsing and classification logic for AngelOne's master dump.
Returns a ParsedInstruments container that the InstrumentManager can
insert without knowing anything about AngelOne's JSON format.

Source: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json

JSON field reference (from AngelOne docs):
  token          — AngelOne's unique numeric identifier for the instrument
  symbol         — Display name / AngelOne tradingsymbol (NOT canonical — may have spaces, mixed case)
  name           — Canonical underlying name: "NIFTY", "BANKNIFTY", "RELIANCE" etc.
  expiry         — Expiry date in "DDMMMYYYY" format (e.g. "27JUN2028"), or empty
  strike         — Strike price * 100 (options), or -1.0 (futures/others)
  lotsize        — Lot size
  instrumenttype — AMXIDX (index), blank (equity), FUTIDX/FUTSTK (futures),
                   OPTIDX/OPTSTK (options)
  exch_seg       — Exchange segment: NSE, BSE, NFO, BFO, MCX, CDS, ...
  tick_size      — Minimum price movement

Processing order matches insert order (FK constraint):
  1. indices  — underlyings must exist before futures/options reference them
  2. equities — stocks on NSE/BSE
  3. futures  — NFO-FUT and BFO-FUT
  4. options  — NFO-OPT and BFO-OPT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Canonical parsed types (identical shape to Zerodha parser — InstrumentManager
# doesn't care which broker produced them)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParsedIndex:
    """Parsed canonical index row from AngelOne instrument JSON."""

    exchange: str
    symbol: str         # canonical — what users write: "NIFTY", "BANKNIFTY"
    broker_symbol: str  # AngelOne's raw symbol field: "Nifty 50", "Nifty Bank"
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str


@dataclass(frozen=True)
class ParsedEquity:
    """Parsed canonical equity row from AngelOne instrument JSON."""

    exchange: str
    symbol: str         # canonical — same as broker_symbol stripped of -EQ suffix
    broker_symbol: str  # AngelOne's raw symbol field: "RELIANCE-EQ"
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str


@dataclass(frozen=True)
class ParsedFuture:
    """Parsed canonical futures row from AngelOne instrument JSON."""

    exchange: str             # NFO or BFO (the derivative exchange, stored in DB)
    symbol: str               # underlying canonical name — "NIFTY", "RELIANCE"
    broker_symbol: str        # AngelOne's tradingsymbol — "NIFTY30MAR26FUT"
    segment: str              # NFO-FUT or BFO-FUT
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    underlying_exchange: str  # NSE for NFO, BSE for BFO


@dataclass(frozen=True)
class ParsedOption:
    """Parsed canonical options row from AngelOne instrument JSON."""

    exchange: str             # NFO or BFO
    symbol: str               # underlying canonical name — "NIFTY", "RELIANCE"
    broker_symbol: str        # AngelOne's tradingsymbol — "NIFTY27FEB2623000CE"
    segment: str              # NFO-OPT or BFO-OPT
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    strike: float
    option_type: str          # CE or PE
    underlying_exchange: str  # NSE for NFO, BSE for BFO


@dataclass
class ParsedInstruments:
    """Container for all parsed instrument groups."""

    indices:  list[ParsedIndex]  = field(default_factory=list)
    equities: list[ParsedEquity] = field(default_factory=list)
    futures:  list[ParsedFuture] = field(default_factory=list)
    options:  list[ParsedOption] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Classification constants
# ---------------------------------------------------------------------------

# instrumenttype == "AMXIDX" → index row (NSE or BSE)
_INDEX_TYPE = "AMXIDX"

# In-scope equity exchanges
_EQUITY_EXCHANGES = {"NSE", "BSE"}

# In-scope derivative exchanges (F&O)
_FUT_EXCHANGES = {"NFO", "BFO"}

# Maps derivative exchange → underlying's cash exchange
_UNDERLYING_EXCHANGE: dict[str, str] = {
    "NFO": "NSE",
    "BFO": "BSE",
}

# AngelOne's instrumenttype for futures (index + stock)
_FUTURE_TYPES = {"FUTIDX", "FUTSTK"}

# AngelOne's instrumenttype for options (index + stock)
_OPTION_TYPES = {"OPTIDX", "OPTSTK"}


# ---------------------------------------------------------------------------
# Expiry parser
#
# AngelOne uses "DDMMMYYYY" format (e.g. "27JUN2028", "24FEB2026").
# ---------------------------------------------------------------------------

def _parse_expiry(raw: str) -> date:
    """Parse AngelOne expiry date in `DDMMMYYYY` format."""
    return datetime.strptime(raw.strip(), "%d%b%Y").date()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse(rows: list[dict[str, Any]]) -> ParsedInstruments:
    """
    Parse AngelOne's instrument master (list of dicts, from JSON)
    into a ParsedInstruments container. Rows outside v1 scope are silently skipped.
    """
    result = ParsedInstruments()

    for row in rows:
        instrument_type = (row.get("instrumenttype") or "").strip()
        exch_seg        = (row.get("exch_seg") or "").strip()

        # --- Indices ---
        if instrument_type == _INDEX_TYPE and exch_seg in _EQUITY_EXCHANGES:
            result.indices.append(_parse_index(row))
            continue

        # --- Equities (instrumenttype is empty/NaN for plain equities) ---
        if not instrument_type and exch_seg in _EQUITY_EXCHANGES:
            symbol: str = (row.get("symbol") or "").strip()
            # Keep plain equities (-EQ suffix) or heuristic plain ones; skip bonds/MFs/etc.
            if symbol.endswith("-EQ") or _is_plain_equity(row):
                result.equities.append(_parse_equity(row))
            continue

        # --- Futures ---
        if instrument_type in _FUTURE_TYPES and exch_seg in _FUT_EXCHANGES:
            result.futures.append(_parse_future(row))
            continue

        # --- Options ---
        if instrument_type in _OPTION_TYPES and exch_seg in _FUT_EXCHANGES:
            result.options.append(_parse_option(row))
            continue

        # MCX, CDS, NCO, BFO bonds, etc. — out of v1 scope, skip

    return result


# ---------------------------------------------------------------------------
# Per-type parsers
# ---------------------------------------------------------------------------

def _parse_index(row: dict[str, Any]) -> ParsedIndex:
    """
    AngelOne index rows (instrumenttype == AMXIDX):
      - symbol field: display name with spaces, mixed case — e.g. "Nifty 50", "Nifty Bank"
        → this becomes broker_symbol (what AngelOne's API expects for WebSocket subscription)
      - name field: clean canonical form — e.g. "NIFTY", "BANKNIFTY"
        → this becomes our canonical symbol stored in the DB

    Token is an integer stored as a string (e.g. "99926000").
    """
    canonical  = (row.get("name") or "").strip()    # "NIFTY", "BANKNIFTY", "SENSEX"
    broker_sym = (row.get("symbol") or "").strip()  # "Nifty 50", "Nifty Bank", "SENSEX"

    return ParsedIndex(
        exchange      = row["exch_seg"].strip(),     # "NSE" or "BSE"
        symbol        = canonical,
        broker_symbol = broker_sym,
        segment       = "INDICES",
        name          = canonical or None,
        lot_size      = int(row.get("lotsize") or 1),
        tick_size     = float(row.get("tick_size") or 0.0),
        broker_token  = str(row["token"]).strip(),
    )


def _parse_equity(row: dict[str, Any]) -> ParsedEquity:
    """
    AngelOne equity rows: instrumenttype is empty, exch_seg is NSE or BSE.
    Symbol may have a "-EQ" suffix (e.g. "RELIANCE-EQ"). We strip it for
    the canonical symbol but keep the full form as broker_symbol.
    """
    broker_sym = (row.get("symbol") or "").strip()   # e.g. "RELIANCE-EQ"
    canonical  = broker_sym.removesuffix("-EQ")       # e.g. "RELIANCE"

    return ParsedEquity(
        exchange      = row["exch_seg"].strip(),
        symbol        = canonical,
        broker_symbol = broker_sym,
        segment       = row["exch_seg"].strip(),     # "NSE" or "BSE"
        name          = (row.get("name") or "").strip() or None,
        lot_size      = int(row.get("lotsize") or 1),
        tick_size     = float(row.get("tick_size") or 0.05),
        broker_token  = str(row["token"]).strip(),
    )


def _parse_future(row: dict[str, Any]) -> ParsedFuture:
    """
    AngelOne futures: FUTIDX (index futures) and FUTSTK (stock futures).
    The `name` field carries the underlying's canonical symbol — same value
    used in our DB. e.g. "NIFTY", "BANKNIFTY", "RELIANCE".
    """
    exch_seg = row["exch_seg"].strip()               # NFO or BFO

    return ParsedFuture(
        exchange            = exch_seg,
        symbol              = (row.get("name") or "").strip(),   # underlying canonical: "NIFTY"
        broker_symbol       = (row.get("symbol") or "").strip(), # "NIFTY30MAR26FUT"
        segment             = f"{exch_seg}-FUT",
        lot_size            = int(row.get("lotsize") or 1),
        tick_size           = float(row.get("tick_size") or 0.05),
        broker_token        = str(row["token"]).strip(),
        expiry              = _parse_expiry(row["expiry"]),
        underlying_exchange = _UNDERLYING_EXCHANGE[exch_seg],
    )


def _parse_option(row: dict[str, Any]) -> ParsedOption:
    """
    AngelOne options: OPTIDX (index options) and OPTSTK (stock options).
    Strike is stored as strike * 100 in AngelOne's master — divide by 100.
    """
    exch_seg = row["exch_seg"].strip()               # NFO or BFO

    # AngelOne stores strike as strike * 100 (e.g. 2300000 → 23000.0)
    raw_strike = float(row.get("strike") or 0)
    strike = raw_strike / 100.0

    # Derive CE/PE from broker_symbol suffix (last 2 chars)
    broker_sym: str = (row.get("symbol") or "").strip()
    option_type = broker_sym[-2:] if len(broker_sym) >= 2 else ""

    return ParsedOption(
        exchange            = exch_seg,
        symbol              = (row.get("name") or "").strip(),   # underlying canonical: "NIFTY"
        broker_symbol       = broker_sym,                        # "NIFTY27FEB2623000CE"
        segment             = f"{exch_seg}-OPT",
        lot_size            = int(row.get("lotsize") or 1),
        tick_size           = float(row.get("tick_size") or 0.05),
        broker_token        = str(row["token"]).strip(),
        expiry              = _parse_expiry(row["expiry"]),
        strike              = strike,
        option_type         = option_type,                       # "CE" or "PE"
        underlying_exchange = _UNDERLYING_EXCHANGE[exch_seg],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Suffix patterns that indicate non-equity NSE/BSE instruments to skip
_NON_EQUITY_SUFFIXES = ("-GS", "-MF", "-SG", "-SM", "-IL", "-BL", "-CB", "-TB")

def _is_plain_equity(row: dict[str, Any]) -> bool:
    """
    Heuristic: keep NSE/BSE rows that look like plain equities.
    Filters out bonds (suffix -GS, -SG), MFs (-MF), SMEs (-SM), etc.
    """
    symbol: str = (row.get("symbol") or "").strip()
    return not any(symbol.endswith(sfx) for sfx in _NON_EQUITY_SUFFIXES)
