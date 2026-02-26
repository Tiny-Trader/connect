# tt-connect: Desired State

## The Goal

A developer using tt-connect never writes broker-specific code.
Broker is a configuration detail, not an architectural one.

---

## Decisions Locked In

### 1. Auth is a Background Lifecycle, Not a User Concern
- Pass credentials once — the library owns the entire auth state machine
- Handles OAuth, TOTP, session persistence, and daily re-login silently
- User initializes once and never thinks about auth again
- Swapping broker does not change any auth-handling code

```python
async with AsyncTTConnect("zerodha", config) as broker:
    # That's it. Session is managed, refreshed, and persisted automatically.
    pass
```

### 2. Typed Instrument Objects + Enums, Not Strings
- Instruments are strongly-typed objects — no magic strings
- Symbols follow NSE official naming conventions as the canonical standard
- tt-connect translates to broker-specific format internally
- Validation uses the live instrument DB — not just type checking
- Invalid expiries, non-existent strikes, unsupported symbols fail at construction, not at broker call time
- Instrument objects are only valid after `TTConnect` is initialized and the DB is fresh

```python
from tt_connect.instruments import Equity, Future, Option
from tt_connect.enums import Exchange, OptionType, ProductType, OrderType, Side

equity = Equity(exchange=Exchange.NSE, symbol="RELIANCE")
future = Future(exchange=Exchange.NSE, symbol="NIFTY", expiry="2025-01-30")
option = Option(exchange=Exchange.NSE, symbol="NIFTY", expiry="2025-01-30", strike=18000, option_type=OptionType.CE)
```

Enums cover all categorical inputs: `Exchange`, `OptionType`, `ProductType`, `OrderType`, `Side`

### 3. One Canonical Data Model
- Every broker response is normalized to a standard shape before it reaches the caller
- No broker-specific keys leak into application code

### 4. One Order Interface

Orders are described with request objects — validated at construction, before any network call:

```python
from tt_connect import PlaceOrderRequest, ModifyOrderRequest

req = PlaceOrderRequest(
    instrument=equity,
    side=Side.BUY,
    qty=10,
    order_type=OrderType.MARKET,
    product=ProductType.CNC,
)
order_id = await broker.place_order(req)

await broker.modify_order(ModifyOrderRequest(order_id=order_id, price=2900.0))
```

### 5. One Streaming Interface

```python
await broker.subscribe([equity, option], on_tick=handler)
```

### 6. Both Sync and Async Clients

Core logic written once, exposed via two client classes. Both support context managers.

```python
# sync
with TTConnect("zerodha", config) as broker:
    broker.place_order(req)

# async
async with AsyncTTConnect("zerodha", config) as broker:
    await broker.place_order(req)
```

### 7. Predictable Lifecycle Errors
- Explicit client state: `CREATED → CONNECTED → CLOSED`
- Typed, catchable exceptions instead of `AssertionError`:
  - `ClientNotConnectedError` — `init()` not called
  - `ClientClosedError` — client already closed; create a new one
- Context managers handle the lifecycle automatically — preferred for all use cases

### 8. Unified Error Handling
- Consistent exception hierarchy — `TTConnectError` and subclasses
- Rate limiting and retryable vs non-retryable errors handled by the library

### 9. Broker is a One-Line Swap
- No strategy or engine code needs to know which broker is active

---

## What the Developer Never Has to Do

- Parse broker-specific response envelopes
- Handle session expiry manually
- Translate symbol formats
- Know which HTTP method or encoding a broker uses
- Write broker-specific error handling
- Manage async resource cleanup in try/finally blocks
