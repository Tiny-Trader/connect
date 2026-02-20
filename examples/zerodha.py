"""
tt-connect: Zerodha — Getting Started
======================================

This example shows the full user-facing API:
  1. Authenticate and initialise
  2. Profile and funds
  3. Instrument resolution (Index, Equity, Future, Option)
  4. Portfolio — holdings and positions
  5. Reports   — order book and trade book
  6. Order management — place, modify, cancel, cancel-all, close-all

Prerequisites
-------------
1. Install the library (from the connect/ directory):
       pip install -e .

2. Get your credentials from https://kite.trade/:
   - api_key      → your Kite Connect app's API key
   - access_token → generated after completing the daily OAuth login flow
                    (use dev/get_token.py for the automated flow)

3. Set environment variables (or .env file):
       export ZERODHA_API_KEY=your_api_key
       export ZERODHA_ACCESS_TOKEN=your_access_token

Run
---
    cd connect/
    python examples/zerodha.py
"""

import os
from datetime import date
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

API_KEY      = os.environ.get("ZERODHA_API_KEY", "")
ACCESS_TOKEN = os.environ.get("ZERODHA_ACCESS_TOKEN", "")

if not API_KEY or not ACCESS_TOKEN:
    raise SystemExit(
        "\nMissing credentials.\n"
        "Set ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN in your environment or .env file.\n"
    )


# ---------------------------------------------------------------------------
# tt-connect: the public API
# ---------------------------------------------------------------------------

from tt_connect import TTConnect
from tt_connect.instruments import Index, Equity, Future, Option
from tt_connect.enums import Exchange, OptionType, Side, ProductType, OrderType

broker = TTConnect("zerodha", config={
    "api_key":      API_KEY,
    "access_token": ACCESS_TOKEN,
})

# TTConnect.__init__ calls login() + seeds the instrument DB automatically.
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

# Future  (nearest weekly/monthly — use a real expiry from the DB)
nifty_fut = Future(
    exchange=Exchange.NSE,
    symbol="NIFTY",
    expiry=date(2026, 2, 24),       # replace with the active expiry
)

# Option
nifty_ce = Option(
    exchange=Exchange.NSE,
    symbol="NIFTY",
    expiry=date(2026, 2, 24),
    strike=25000.0,
    option_type=OptionType.CE,
)

for inst in [nifty, sensex, reliance, tcs, nifty_fut, nifty_ce]:
    token = broker._run(broker._async._resolve(inst))
    print(f"  {inst.exchange}:{inst.symbol:<20} → {token}")

print()


# ---------------------------------------------------------------------------
# 4. Portfolio
# ---------------------------------------------------------------------------

print("── Holdings ────────────────────────────")
holdings = broker.get_holdings()
if holdings:
    for h in holdings:
        print(f"  {h.instrument.symbol:<15} qty={h.qty:>6}  "
              f"avg=₹{h.avg_price:.2f}  ltp=₹{h.ltp:.2f}  "
              f"pnl=₹{h.pnl:.2f}  ({h.pnl_percent:+.2f}%)")
else:
    print("  (no holdings)")
print()

print("── Positions (open) ────────────────────")
positions = broker.get_positions()
if positions:
    for p in positions:
        print(f"  {p.instrument.exchange}:{p.instrument.symbol:<20} qty={p.qty:>6}  "
              f"avg=₹{p.avg_price:.2f}  ltp=₹{p.ltp:.2f}  "
              f"pnl=₹{p.pnl:.2f}  product={p.product}")
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
        print(f"  {o.id}  {sym:<20}  {o.side}  qty={o.qty}  "
              f"status={o.status}  product={o.product}")
    if len(orders) > 5:
        print(f"  ... and {len(orders) - 5} more")
else:
    print("  (no orders today)")
print()

print("── Trade book ──────────────────────────")
trades = broker.get_trades()
if trades:
    for t in trades[:5]:
        print(f"  {t.order_id}  {t.instrument.symbol:<20}  {t.side}  "
              f"qty={t.qty}  avg=₹{t.avg_price:.2f}  value=₹{t.trade_value:.2f}")
    if len(trades) > 5:
        print(f"  ... and {len(trades) - 5} more")
else:
    print("  (no fills today)")
print()


# ---------------------------------------------------------------------------
# 6. Order management (commented out — uncomment to execute)
# ---------------------------------------------------------------------------

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
# broker.modify_order(order_id, price=801.00, order_type=OrderType.LIMIT, qty=1)

# Cancel a specific order
# broker.cancel_order(order_id)

# Cancel every open order
# cancelled, failed = broker.cancel_all_orders()
# print(f"Cancelled {len(cancelled)} orders, {len(failed)} failed")

# Close every open position with market orders
# placed, failed = broker.close_all_positions()
# print(f"Closed {len(placed)} positions, {len(failed)} failed")
