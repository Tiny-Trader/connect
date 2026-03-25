# Orders

!!! warning "Broker differences"
    AngelOne does not support `get_order(order_id)` — use `get_orders()` and filter by ID instead. See [operation notes](reference/operation-notes.md) for full per-broker behavior.

## Core actions
- place order
- modify order
- cancel order
- list orders

## Place order (market)
```python
from tt_connect import TTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    order_id = broker.place_order(
        instrument=Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        side=Side.BUY,
        qty=1,
        order_type=OrderType.MARKET,
        product=ProductType.CNC,
    )
    print("placed:", order_id)
```

## Place order (limit)
```python
order_id = broker.place_order(
    instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
    side=Side.BUY,
    qty=10,
    order_type=OrderType.LIMIT,
    product=ProductType.CNC,
    price=800.0,
)
```

## Modify and cancel
```python
broker.modify_order(order_id=order_id, price=801.0, qty=10)
broker.cancel_order(order_id)
```

## Read orders
```python
orders = broker.get_orders()
for o in orders:
    print(o.id, o.status, o.qty)
```

## Order flow
`PENDING -> OPEN -> COMPLETE` or `CANCELLED` or `REJECTED`

## Good patterns
- save returned order id
- check order state after placement
- handle rejection and avoid blind retries

## What's next?
- [Trades](trades.md) — check fills after placing orders
- [Positions](positions.md) — monitor net open quantity
- [GTT (Trigger Orders)](gtt.md) — set up automated trigger-based orders

## See also
- [Client methods (order APIs)](reference/clients.md)
- [Models (`Order`)](reference/models.md)
- [Enums (`OrderType`, `ProductType`, `Side`, `OrderStatus`)](reference/enums.md)
- [Exceptions](reference/exceptions.md)
- [Broker operation notes](reference/operation-notes.md)
- [Recipe: First order](recipes/first-order.md)
- [Recipe: Cancel all open orders](recipes/cancel-all-open-orders.md)
