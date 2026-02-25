# Getting Started

This guide gets you from install to first order-flow call with `tt-connect`.

## 1. Prerequisites

- Python `3.11+`
- Poetry
- Broker credentials (Zerodha or AngelOne)

## 2. Install

```bash
cd connect
poetry install
```

## 3. Configure Credentials

Create `.env` (or pass config directly):

```bash
cp .env.example .env
```

Typical config shapes:

- Zerodha (manual token)
- AngelOne (manual or auto)

See `docs/USAGE_EXAMPLES.md` for full credential examples.

## 4. Initialize Client

The recommended pattern is a context manager — resources are released automatically:

```python
from tt_connect import AsyncTTConnect

async with AsyncTTConnect("zerodha", {
    "api_key": "...",
    "access_token": "...",
}) as broker:
    profile = await broker.get_profile()
    # broker.close() is called automatically on exit
```

Or manage the lifecycle manually:

```python
broker = AsyncTTConnect("zerodha", {"api_key": "...", "access_token": "..."})
await broker.init()
# ... operations ...
await broker.close()
```

`init()` performs auth and instrument master setup. The client tracks state internally —
calling methods before `init()` raises `ClientNotConnectedError`; calling them after
`close()` raises `ClientClosedError`.

## 5. Run Basic Calls

```python
profile = await broker.get_profile()
funds   = await broker.get_funds()
positions = await broker.get_positions()
```

All responses are normalized to canonical models in `tt_connect/models.py`.

## 6. Place an Order

Orders are described with a `PlaceOrderRequest` model:

```python
from tt_connect import PlaceOrderRequest
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

req = PlaceOrderRequest(
    instrument=Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
    side=Side.BUY,
    qty=1,
    order_type=OrderType.MARKET,
    product=ProductType.CNC,
)
order_id = await broker.place_order(req)
```

## 7. Modify or Cancel

```python
from tt_connect import ModifyOrderRequest

await broker.modify_order(ModifyOrderRequest(order_id=order_id, price=2900.0))
await broker.cancel_order(order_id)
```

## 8. Next Reads

- API examples: [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md)
- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Legal/risk notices: [../DISCLAIMER.md](../DISCLAIMER.md)
