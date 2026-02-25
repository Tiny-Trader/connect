# tt-connect: Usage Examples

---

## 1. Initialization

### Context Manager (recommended)

```python
from tt_connect import AsyncTTConnect

async with AsyncTTConnect("zerodha", {
    "api_key": "xxx",
    "access_token": "xxx",
}) as broker:
    profile = await broker.get_profile()
    # close() called automatically
```

```python
from tt_connect import TTConnect

with TTConnect("angelone", {
    "auth_mode": "auto",
    "api_key": "xxx",
    "client_id": "xxx",
    "pin": "1234",
    "totp_secret": "JBSWY3DPEHPK3PXP",
}) as broker:
    profile = broker.get_profile()
```

### Manual Lifecycle

```python
from tt_connect import AsyncTTConnect
from tt_connect.enums import OnStale

broker = AsyncTTConnect("zerodha", {
    "api_key": "xxx",
    "access_token": "xxx",
    "on_stale": OnStale.FAIL,
})
await broker.init()
# ... operations ...
await broker.close()
```

Session is managed automatically. No `login()` call. No token refresh logic.
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
```

---

## 3. Profile & Funds

```python
profile = await broker.get_profile()
# Profile(client_id='XY1234', name='John Doe', email='john@example.com')

funds = await broker.get_funds()
# Fund(available=125000.0, used=45000.0, total=170000.0)
```

---

## 4. Portfolio

```python
holdings = await broker.get_holdings()
# [
#   Holding(instrument=Equity(NSE, RELIANCE), qty=10, avg_price=2800.0, ltp=2950.0, pnl=1500.0),
#   Holding(instrument=Equity(NSE, INFY),     qty=5,  avg_price=1500.0, ltp=1480.0, pnl=-100.0),
# ]

positions = await broker.get_positions()
# [
#   Position(instrument=Future(NFO, NIFTY, 2025-01-30), qty=50, avg_price=23100.0, ltp=23250.0, pnl=7500.0),
# ]
```

---

## 5. Orders

```python
from tt_connect import PlaceOrderRequest, ModifyOrderRequest
from tt_connect.enums import Side, ProductType, OrderType

# Place a market order
req = PlaceOrderRequest(
    instrument=reliance,
    side=Side.BUY,
    qty=10,
    order_type=OrderType.MARKET,
    product=ProductType.CNC,
)
order_id = await broker.place_order(req)

# Place a limit order
req = PlaceOrderRequest(
    instrument=nifty_ce,
    side=Side.BUY,
    qty=50,
    order_type=OrderType.LIMIT,
    product=ProductType.MIS,
    price=120.50,
)
order_id = await broker.place_order(req)

# Modify
await broker.modify_order(ModifyOrderRequest(order_id=order_id, price=118.00, qty=50))

# Cancel
await broker.cancel_order(order_id)

# Cancel all open orders
cancelled, failed = await broker.cancel_all_orders()

# Order status
order = await broker.get_order(order_id)
# Order(id='...', side=BUY, qty=50, status=COMPLETE, filled_qty=50, avg_price=119.25)

# Full order book
orders = await broker.get_orders()
```

---

## 6. Streaming (Async)

```python
from tt_connect.models import Tick

async def on_tick(tick: Tick) -> None:
    print(tick)
    # Tick(instrument=Equity(NSE, RELIANCE), ltp=2952.5, volume=1200340, timestamp=...)

async with AsyncTTConnect("angelone", config) as broker:
    await broker.subscribe(
        instruments=[reliance, nifty_ce, nifty_fut],
        on_tick=on_tick,
    )
```

---

## 7. Broker Swap — The Point of All This

```python
# Strategy works on Zerodha today
async with AsyncTTConnect("zerodha", zerodha_config) as broker:
    holdings = await broker.get_holdings()
    await broker.place_order(PlaceOrderRequest(instrument=reliance, qty=10, side=Side.BUY, ...))

# Move to AngelOne tomorrow — zero other changes
async with AsyncTTConnect("angelone", angelone_config) as broker:
    holdings = await broker.get_holdings()
    await broker.place_order(PlaceOrderRequest(instrument=reliance, qty=10, side=Side.BUY, ...))
```

---

## 8. Error Handling

```python
from tt_connect.exceptions import (
    AuthenticationError,
    ClientNotConnectedError,
    ClientClosedError,
    InsufficientFundsError,
    InvalidOrderError,
    RateLimitError,
    TTConnectError,
)

# Lifecycle errors
broker = AsyncTTConnect("zerodha", config)
try:
    await broker.get_profile()
except ClientNotConnectedError:
    # forgot to call await broker.init()
    await broker.init()

# Order errors
try:
    await broker.place_order(req)
except InsufficientFundsError:
    # not enough margin
except InvalidOrderError as e:
    # bad order params — validated before network call
except RateLimitError:
    # slow down
except TTConnectError as e:
    # catch-all for anything else
    print(e.broker_code)  # raw broker error code if available
```

---

## 9. Unsupported Features Fail Immediately

```python
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange

gold = Equity(exchange=Exchange.MCX, symbol="GOLD")

async with AsyncTTConnect("zerodha", config) as broker:
    await broker.place_order(PlaceOrderRequest(instrument=gold, ...))
    # UnsupportedFeatureError: Zerodha does not support MCX segment
    # Raised before any HTTP call is made.
```
