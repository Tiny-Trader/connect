# Recipe: First Order

This is the shortest safe path to place your first order.

## 1) Create client
```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}
broker = TTConnect("zerodha", config)
```

## 2) Check funds
```python
funds = broker.get_funds()
print("Available:", funds.available)
```

## 3) Place a small order
```python
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

order_id = broker.place_order(
    instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
    side=Side.BUY,
    qty=1,
    order_type=OrderType.MARKET,
    product=ProductType.CNC,
)
print("Order ID:", order_id)
```

## 4) Confirm status
```python
orders = broker.get_orders()
match = next((o for o in orders if o.id == order_id), None)
print(match.status if match else "not found")
```

## 5) Close client
```python
broker.close()
```

## Notes
- Use very small quantity for first run.
- If rejected, print full order details and verify product/order type.

## What's next?
- [Cancel all open orders](cancel-all-open-orders.md) — clean up during testing
- [Stream and store live ticks](stream-and-store-live-ticks.md) — get live market data
- [Errors & Retries](../errors-and-retries.md) — handle failures in production

## Related reference
- [Client methods (orders)](../reference/clients.md)
- [Models (`Order`)](../reference/models.md)
- [Enums (`OrderType`, `ProductType`, `Side`)](../reference/enums.md)
- [Troubleshooting: Order rejected](../troubleshooting/order-rejected.md)
