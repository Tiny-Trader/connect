# tt-connect: Usage Examples

---

## 1. Initialization

```python
from tt_connect import TTConnect
from tt_connect.enums import OnStale

# Initialize with Auto Mode (e.g., AngelOne: TTConnect handles TOTP login and session caching)
broker = TTConnect("angelone", config={
    "auth_mode": "auto",
    "api_key": "xxx",
    "client_id": "xxx",
    "pin": "1234",
    "totp_secret": "JBSWY3DPEHPK3PXP",
    "cache_session": True,
    "on_stale": OnStale.FAIL,
})

# Initialize with Manual Mode (e.g., Zerodha: providing a pre-generated token)
from tt_connect import AsyncTTConnect

async_broker = AsyncTTConnect("zerodha", config={
    "auth_mode": "manual",
    "api_key": "xxx",
    "access_token": "xxx",
})
```

Session is managed automatically. No `login()` call. No token refresh logic. No daily re-login code.
Swap `"zerodha"` for `"angelone"` — nothing else changes.

---

## 2. Instruments

```python
from tt_connect.instruments import Equity, Future, Option
from tt_connect.enums import Exchange, OptionType

# Equity
reliance = Equity(exchange=Exchange.NSE, symbol="RELIANCE")

# Future
nifty_fut = Future(exchange=Exchange.NFO, symbol="NIFTY", expiry="2025-01-30")

# Option
nifty_ce = Option(
    exchange=Exchange.NFO,
    symbol="NIFTY",
    expiry="2025-01-30",
    strike=23000,
    option_type=OptionType.CE,
)

# Bad inputs fail immediately — before any network call
bad = Future(exchange=Exchange.NFO, symbol="NIFTY", expiry="2025-13-99")
# InstrumentNotFoundError: No NIFTY future with expiry 2025-13-99 exists
```

---

## 3. Profile & Funds

```python
profile = broker.get_profile()
# Profile(client_id='XY1234', name='John Doe', email='john@example.com')

funds = broker.get_funds()
# Fund(available=125000.0, used=45000.0, total=170000.0)
```

---

## 4. Portfolio

```python
holdings = broker.get_holdings()
# [
#   Holding(instrument=Equity(NSE, RELIANCE), qty=10, avg_price=2800.0, ltp=2950.0, pnl=1500.0),
#   Holding(instrument=Equity(NSE, INFY),     qty=5,  avg_price=1500.0, ltp=1480.0, pnl=-100.0),
# ]

positions = broker.get_positions()
# [
#   Position(instrument=Future(NFO, NIFTY, 2025-01-30), qty=50, avg_price=23100.0, ltp=23250.0, pnl=7500.0),
# ]
```

---

## 5. Orders

```python
from tt_connect.enums import Side, ProductType, OrderType

# Place
order_id = broker.place_order(
    instrument=reliance,
    qty=10,
    side=Side.BUY,
    product=ProductType.CNC,
    order_type=OrderType.MARKET,
)

# Place limit order
order_id = broker.place_order(
    instrument=nifty_ce,
    qty=50,
    side=Side.BUY,
    product=ProductType.MIS,
    order_type=OrderType.LIMIT,
    price=120.50,
)

# Modify
broker.modify_order(order_id=order_id, price=118.00, qty=50)

# Cancel
broker.cancel_order(order_id=order_id)

# Order status
order = broker.get_order(order_id=order_id)
# Order(id='...', instrument=Option(NFO,NIFTY,...), side=BUY, qty=50, status=COMPLETE, filled_qty=50, avg_price=119.25)

# Order book
orders = broker.get_orders()
```

---

## 6. Streaming (Async)

```python
async def on_tick(tick):
    print(tick)
    # Tick(instrument=Equity(NSE, RELIANCE), ltp=2952.5, volume=1200340, oi=None, timestamp=...)

async def on_order_update(order):
    print(order)
    # Order(id='...', status=COMPLETE, filled_qty=10, avg_price=2952.5)

async def main():
    broker = AsyncTTConnect("angelone", config={...})

    await broker.subscribe(
        instruments=[reliance, nifty_ce, nifty_fut],
        on_tick=on_tick,
        on_order_update=on_order_update,
    )
```

---

## 7. Broker Swap — The Point of All This

```python
# Strategy works on Zerodha today
broker = TTConnect("zerodha", config=zerodha_config)

# Move to AngelOne tomorrow — zero other changes
broker = TTConnect("angelone", config=angelone_config)

# Instruments, orders, streaming — all identical
holdings = broker.get_holdings()
broker.place_order(instrument=reliance, qty=10, side=Side.BUY, ...)
```

---

## 8. Error Handling

```python
from tt_connect.exceptions import (
    AuthenticationError,
    InsufficientFundsError,
    InvalidOrderError,
    RateLimitError,
    TTConnectError,
)

try:
    broker.place_order(...)
except InsufficientFundsError:
    # not enough margin
except InvalidOrderError as e:
    # bad order params
except RateLimitError:
    # slow down
except TTConnectError as e:
    # catch-all for anything else
```

---

## 9. Unsupported Features Fail Immediately

```python
from tt_connect.instruments import Commodity
from tt_connect.enums import Exchange

gold = Commodity(exchange=Exchange.MCX, symbol="GOLD")

broker = TTConnect("zerodha", config={...})
broker.place_order(instrument=gold, ...)
# UnsupportedFeatureError: Zerodha does not support MCX segment
```
