"""
tt-connect: AngelOne — Getting Started
=======================================

This example shows the full user-facing API for AngelOne:
  1. Authenticate and initialise (auto mode — TOTP; or manual mode)
  2. Profile and funds
  3. Instrument resolution (Index, Equity, Future, Option)
  4. Portfolio — holdings and positions
  5. Reports   — order book and trade book
  6. Order management — place, modify, cancel, cancel-all, close-all
  7. WebSocket — real-time tick streaming

Prerequisites
-------------
1. Install the library:
       pip install tt-connect

2. Get your AngelOne Smart API credentials from https://smartapi.angelbroking.com/:
   - api_key     → your Smart API app key
   - client_id   → your AngelOne client / user ID
   - pin         → your 4-digit trading PIN
   - totp_secret → the Base32 secret shown when you enable TOTP in the app
                   (scan the QR code with a TOTP app and note the secret key)

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
    python examples/angelone.py
"""

import asyncio
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------


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

API_KEY     = os.environ.get("ANGELONE_API_KEY", "")
CLIENT_ID   = os.environ.get("ANGELONE_CLIENT_ID", "")
PIN         = os.environ.get("ANGELONE_PIN", "")
TOTP_SECRET = os.environ.get("ANGELONE_TOTP_SECRET", "")

# Only required for manual mode:
ACCESS_TOKEN = os.environ.get("ANGELONE_ACCESS_TOKEN", "")

# Decide which mode to run.
# Switch to "manual" if you have a pre-obtained JWT token and no TOTP secret.
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


# ---------------------------------------------------------------------------
# tt-connect: the public API
# ---------------------------------------------------------------------------

from tt_connect import TTConnect, setup_logging  # noqa: E402
from tt_connect.instruments import Index, Equity, Future, Option  # noqa: E402
from tt_connect.enums import Exchange, OptionType  # noqa: E402

# ---------------------------------------------------------------------------
# Structured logging (optional)
#
# Call setup_logging() once before constructing the client to enable
# structured output.  Each event emits one JSON line to stderr, e.g.:
#   {"ts":"...","level":"INFO","logger":"tt_connect.adapters.angelone.auth",
#    "message":"AngelOne login successful for C123456",
#    "event":"auth.login","broker":"angelone","mode":"auto"}
#
# Text format alternative: setup_logging(fmt="text")
# ---------------------------------------------------------------------------

setup_logging()   # JSON to stderr, INFO level

# ---------------------------------------------------------------------------
# Auth mode A: AUTO (default for AngelOne)
#   tt-connect performs the full TOTP login and handles token refresh.
#   No human interaction required after the first run.
#   Recommended for production algo-trading.
#
# Auth mode B: MANUAL
#   You supply a pre-obtained JWT access_token.
#   Useful when you already manage sessions externally.
# ---------------------------------------------------------------------------

if USE_AUTO_MODE:
    config = {
        "auth_mode":    "auto",          # optional — "auto" is already the AngelOne default
        "api_key":      API_KEY,
        "client_id":    CLIENT_ID,
        "pin":          PIN,
        "totp_secret":  TOTP_SECRET,
        "cache_session": True,           # writes _cache/angelone_session.json
                                         # avoids a re-login on every restart until midnight IST
    }
else:
    config = {
        "auth_mode":    "manual",
        "api_key":      API_KEY,
        "access_token": ACCESS_TOKEN,    # the jwtToken from a prior login
        "cache_session": False,
    }

broker = TTConnect("angelone", config=config)

# TTConnect.__init__ calls login() + seeds the instrument DB automatically.
# In auto mode, credentials are validated and a JWT is obtained via TOTP.
# No manual session management required.


# ---------------------------------------------------------------------------
# 1. Profile
# ---------------------------------------------------------------------------

profile = broker.get_profile()

print("── Profile ─────────────────────────────")
print(f"  Client ID : {profile.client_id}")
print(f"  Name      : {profile.name}")
print(f"  Email     : {profile.email}")
print(f"  Phone     : {profile.phone or '—'}")
print()


# ---------------------------------------------------------------------------
# 2. Funds
# ---------------------------------------------------------------------------

funds = broker.get_funds()

print("── Funds ───────────────────────────────")
print(f"  Available      : ₹{funds.available:,.2f}")
print(f"  Used (debits)  : ₹{funds.used:,.2f}")
print(f"  Total (net)    : ₹{funds.total:,.2f}")
print(f"  Collateral     : ₹{funds.collateral:,.2f}")
print(f"  M2M Unrealized : ₹{funds.m2m_unrealized:,.2f}")
print(f"  M2M Realized   : ₹{funds.m2m_realized:,.2f}")
print()


# ---------------------------------------------------------------------------
# 3. Instrument resolution
#
# broker._resolve() is the internal method used by place_order() automatically.
# You never need to call it directly — shown here only to illustrate the model.
# ---------------------------------------------------------------------------

print("── Instrument resolution ───────────────")

# Index
nifty  = Index(exchange=Exchange.NSE, symbol="NIFTY")
sensex = Index(exchange=Exchange.BSE, symbol="SENSEX")

# Equity
reliance = Equity(exchange=Exchange.NSE, symbol="RELIANCE")
tcs      = Equity(exchange=Exchange.BSE, symbol="TCS")

# Use the public instrument APIs instead of reaching into the DB directly.
futures = broker.get_futures(nifty)
option_expiries = broker.get_expiries(nifty)
if not futures:
    print("  [No NIFTY futures available in the instrument DB.]")
    raise RuntimeError("Expected at least one NIFTY future in the refreshed instrument DB.")
if not option_expiries:
    print("  [No NIFTY option expiries available in the instrument DB.]")
    raise RuntimeError("Expected at least one NIFTY option expiry in the refreshed instrument DB.")

nearest_future_expiry = futures[0].expiry
nearest_option_expiry = option_expiries[0]
print(f"  [Using nearest NIFTY future expiry: {nearest_future_expiry}]")
print(f"  [Using nearest NIFTY option expiry: {nearest_option_expiry}]")

# Future
nifty_fut = Future(
    exchange=Exchange.NFO,
    symbol="NIFTY",
    expiry=nearest_future_expiry,
)

# Option
nifty_ce = Option(
    exchange=Exchange.NFO,
    symbol="NIFTY",
    expiry=nearest_option_expiry,
    strike=25000.0,
    option_type=OptionType.CE,
)

for inst in [nifty, sensex, reliance, tcs, nifty_fut, nifty_ce]:
    # This reaches into private internals purely for illustration. Production
    # code should rely on public methods like place_order(), which resolve
    # canonical instruments automatically.
    token = broker._run(broker._async._core._resolve(inst))
    print(f"  {inst.exchange}:{inst.symbol:<20} → {token}")

print()


# ---------------------------------------------------------------------------
# 4. Portfolio
# ---------------------------------------------------------------------------

print("── Holdings ────────────────────────────")
holdings = broker.get_holdings()
if holdings:
    for h in holdings:
        print(
            f"  {h.instrument.symbol:<15} qty={h.qty:>6}  "
            f"avg=₹{h.avg_price:.2f}  ltp=₹{h.ltp:.2f}  "
            f"pnl=₹{h.pnl:.2f}  ({h.pnl_percent:+.2f}%)"
        )
else:
    print("  (no holdings)")
print()

print("── Positions (open) ────────────────────")
positions = broker.get_positions()
if positions:
    for p in positions:
        print(
            f"  {p.instrument.exchange}:{p.instrument.symbol:<20} qty={p.qty:>6}  "
            f"avg=₹{p.avg_price:.2f}  ltp=₹{p.ltp:.2f}  "
            f"pnl=₹{p.pnl:.2f}  product={p.product}"
        )
else:
    print("  (no open positions)")
print()


# ---------------------------------------------------------------------------
# 5. Reports
# ---------------------------------------------------------------------------

print("── Order book ──────────────────────────")
orders = broker.get_orders()
if orders:
    for o in orders[:5]:
        sym = o.instrument.symbol if o.instrument else "—"
        print(f"  {o.id}  {sym:<20}  {o.side}  qty={o.qty}  status={o.status}  product={o.product}")
    if len(orders) > 5:
        print(f"  ... and {len(orders) - 5} more")
else:
    print("  (no orders today)")
print()

# Note: AngelOne does not support fetching a single order by ID.
# Use get_orders() and filter by order_id yourself:
#
#   target = next((o for o in orders if o.id == "my_order_id"), None)

print("── Trade book ──────────────────────────")
trades = broker.get_trades()
if trades:
    for t in trades[:5]:
        print(
            f"  {t.order_id}  {t.instrument.symbol:<20}  {t.side}  "
            f"qty={t.qty}  avg=₹{t.avg_price:.2f}  value=₹{t.trade_value:.2f}"
        )
    if len(trades) > 5:
        print(f"  ... and {len(trades) - 5} more")
else:
    print("  (no fills today)")
print()


# ---------------------------------------------------------------------------
# 6. Order management (commented out — uncomment to execute)
# ---------------------------------------------------------------------------

from tt_connect.enums import Side, ProductType, OrderType  # noqa: E402, F401

# Place a limit order
# order_id = broker.place_order(
#     instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
#     qty=1,
#     side=Side.BUY,
#     product=ProductType.CNC,
#     order_type=OrderType.LIMIT,
#     price=800.00,
# )
# print(f"Placed order: {order_id}")

# Modify it
# broker.modify_order(
#     order_id=order_id,
#     price=801.00,
#     order_type=OrderType.LIMIT,
#     qty=1,
# )

# Cancel a specific order
# broker.cancel_order(order_id)

# Cancel every open order
# cancelled, failed = broker.cancel_all_orders()
# print(f"Cancelled {len(cancelled)} orders, {len(failed)} failed")

# Close every open position with market orders
# placed, failed = broker.close_all_positions()
# print(f"Closed {len(placed)} positions, {len(failed)} failed")


# ---------------------------------------------------------------------------
# 7. Async API & WebSocket streaming
#
# tt-connect is built strictly async-first. The `AsyncTTConnect` class provides
# the exact same API but returns awaiting coroutines.
#
# AngelOne streams in SNAP_QUOTE mode automatically — every tick includes ltp,
# volume, oi, bid, and ask. No extra configuration needed.
# ---------------------------------------------------------------------------

async def run_async_demo() -> None:
    print("── Async API & WebSockets ──────────────")
    from tt_connect import AsyncTTConnect

    # Initialize the fully async client
    async_broker = AsyncTTConnect("angelone", config=config)
    await async_broker.init()

    # Fetch funds asynchronously just as an example
    funds = await async_broker.get_funds()
    print(f"  [Async] Available Funds: ₹{funds.available:,.2f}")

    # WebSocket setup — streams in SNAP_QUOTE mode (ltp, volume, oi, bid, ask)
    instruments = [
        Index(exchange=Exchange.NSE, symbol="NIFTY"),
        Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
    ]

    def on_tick(tick) -> None:
        parts = [
            f"  TICK  {tick.instrument.exchange}:{tick.instrument.symbol:<20}",
            f"  ltp=₹{tick.ltp:.2f}",
        ]
        if tick.volume is not None:
            parts.append(f"  vol={tick.volume}")
        if tick.oi is not None:
            parts.append(f"  oi={tick.oi}")
        if tick.bid is not None and tick.ask is not None:
            parts.append(f"  bid=₹{tick.bid:.2f}  ask=₹{tick.ask:.2f}")
        print("".join(parts))

    print("── Streaming ticks (10 seconds) ────────")
    await async_broker.subscribe(instruments, on_tick)

    # Stream for a short time
    await asyncio.sleep(10)

    await async_broker.unsubscribe(instruments)
    await async_broker.close()
    print("── Stream closed ───────────────────────")

# Uncomment to run the async demo:
# asyncio.run(run_async_demo())
