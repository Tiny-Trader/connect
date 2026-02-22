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

```python
from tt_connect import AsyncTTConnect

broker = AsyncTTConnect("zerodha", {
    "api_key": "...",
    "access_token": "...",
})
await broker.init()
```

`init()` performs auth and instrument master setup.

## 5. Run Basic Calls

```python
profile = await broker.get_profile()
funds = await broker.get_funds()
positions = await broker.get_positions()
```

All responses are normalized to canonical models in `tt_connect/models.py`.

## 6. Place an Order

```python
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

instrument = Equity(exchange=Exchange.NSE, symbol="RELIANCE")
order_id = await broker.place_order(
    instrument=instrument,
    qty=1,
    side=Side.BUY,
    product=ProductType.CNC,
    order_type=OrderType.MARKET,
)
```

## 7. Close Resources

```python
await broker.close()
```

## 8. Next Reads

- API examples: [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md)
- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Legal/risk notices: [../DISCLAIMER.md](../DISCLAIMER.md)
