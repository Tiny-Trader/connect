"""
tt-connect: AngelOne Instrument Store
=====================================

This example shows the standalone discovery API over the local instrument DB.
`InstrumentStore` itself does not log in or refresh data. The main client is
initialized briefly first so the cached DB is seeded and up to date.

What it covers
--------------
1. Seed/refresh the local DB through `TTConnect`
2. Open `InstrumentStore`
3. List derivative-enabled underlyings
4. Fetch instrument metadata
5. Find expiries for an underlying
6. Build an option chain for a chosen expiry
7. Run a raw SQL query as an escape hatch

Prerequisites
-------------
1. Install the library (from the connect/ directory):
       pip install -e .

2. Get your AngelOne Smart API credentials from https://smartapi.angelbroking.com/:
   - api_key     → your Smart API app key
   - client_id   → your AngelOne client / user ID
   - pin         → your 4-digit trading PIN
   - totp_secret → the Base32 secret shown when you enable TOTP in the app

3. Set environment variables (or .env file):
       export ANGELONE_API_KEY=your_api_key
       export ANGELONE_CLIENT_ID=your_client_id
       export ANGELONE_PIN=your_pin
       export ANGELONE_TOTP_SECRET=your_totp_secret

   For manual mode (you pre-obtain the JWT token yourself):
       export ANGELONE_ACCESS_TOKEN=your_jwt_token

Run
---
    cd connect/
    python examples/angelone_store.py
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_env() -> None:
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

API_KEY = os.environ.get("ANGELONE_API_KEY", "")
CLIENT_ID = os.environ.get("ANGELONE_CLIENT_ID", "")
PIN = os.environ.get("ANGELONE_PIN", "")
TOTP_SECRET = os.environ.get("ANGELONE_TOTP_SECRET", "")
ACCESS_TOKEN = os.environ.get("ANGELONE_ACCESS_TOKEN", "")

USE_AUTO_MODE = bool(CLIENT_ID and PIN and TOTP_SECRET)

if not API_KEY:
    raise SystemExit(
        "\nMissing credentials.\n"
        "Set ANGELONE_API_KEY (and the other required vars) in your environment or .env file.\n"
    )

if not USE_AUTO_MODE and not ACCESS_TOKEN:
    raise SystemExit(
        "\nCannot use manual mode: ANGELONE_ACCESS_TOKEN is not set.\n"
        "Either provide CLIENT_ID + PIN + TOTP_SECRET for auto mode, "
        "or set ANGELONE_ACCESS_TOKEN for manual mode.\n"
    )


from tt_connect import InstrumentStore, TTConnect, setup_logging  # noqa: E402
from tt_connect.enums import Exchange  # noqa: E402
from tt_connect.instruments import Equity, Future, Index, Option  # noqa: E402


setup_logging()

if USE_AUTO_MODE:
    config = {
        "auth_mode": "auto",
        "api_key": API_KEY,
        "client_id": CLIENT_ID,
        "pin": PIN,
        "totp_secret": TOTP_SECRET,
        "cache_session": True,
    }
else:
    config = {
        "auth_mode": "manual",
        "api_key": API_KEY,
        "access_token": ACCESS_TOKEN,
        "cache_session": False,
    }


def main() -> None:
    print("── Refresh Instrument DB ──────────────")
    with TTConnect("angelone", config):
        print("  Instrument DB refreshed from broker")
    print()

    with InstrumentStore("angelone") as store:
        print("── Derivative Underlyings (NSE) ───────")
        underlyings = store.list_instruments(exchange=Exchange.NSE, has_derivatives=True)
        for inst in underlyings[:10]:
            kind = "INDEX" if isinstance(inst, Index) else "EQUITY"
            print(f"  {kind:<6} {inst.exchange}:{inst.symbol}")
        if len(underlyings) > 10:
            print(f"  ... and {len(underlyings) - 10} more")
        print()

        nifty = Index(exchange=Exchange.NSE, symbol="NIFTY")
        info = store.get_instrument_info(nifty)

        print("── Instrument Info ────────────────────")
        print(f"  Symbol    : {info.instrument.exchange}:{info.instrument.symbol}")
        print(f"  Name      : {info.name or '—'}")
        print(f"  Segment   : {info.segment}")
        print(f"  Lot Size  : {info.lot_size}")
        print(f"  Tick Size : {info.tick_size}")
        print()

        expiries = store.get_expiries(nifty)
        print("── Expiries ───────────────────────────")
        for expiry in expiries[:5]:
            print(f"  {expiry}")
        if len(expiries) > 5:
            print(f"  ... and {len(expiries) - 5} more")
        print()

        print("── NIFTY Futures ─────────────────────")
        futures = store.list_instruments(
            instrument_type=Future,
            underlying=nifty,
            limit=3,
        )
        for future in futures:
            print(f"  {future.exchange}:{future.symbol} {future.expiry}")
        if not futures:
            print("  (no futures found)")
        print()

        if expiries:
            expiry = expiries[0]
            calls = store.list_instruments(
                instrument_type=Option,
                underlying=nifty,
                expiry=expiry,
                limit=5,
            )
            chain = store.get_option_chain(nifty, expiry)
            print(f"── Option Chain: {nifty.symbol} {expiry} ─────")
            for entry in chain.entries[:10]:
                ce = "CE" if entry.ce is not None else "--"
                pe = "PE" if entry.pe is not None else "--"
                print(f"  strike={entry.strike:>8.2f}  {ce}  {pe}")
            if len(chain.entries) > 10:
                print(f"  ... and {len(chain.entries) - 10} more strikes")
            print(f"  first {len(calls)} contracts via list_instruments()")
            print()

        reliance = Equity(exchange=Exchange.NSE, symbol="RELIANCE")
        rel_expiries = store.get_expiries(reliance)
        print("── RELIANCE Expiries ──────────────────")
        for expiry in rel_expiries[:5]:
            print(f"  {expiry}")
        if not rel_expiries:
            print("  (no expiries found)")
        print()

        rows = store.execute(
            """
            SELECT COUNT(*)
            FROM instruments
            """
        )
        print("── Raw SQL ────────────────────────────")
        print(f"  instrument rows in DB: {rows[0][0]}")


if __name__ == "__main__":
    main()
