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
from tt_connect import PlaceOrderRequest
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

req = PlaceOrderRequest(
    instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
    side=Side.BUY,
    qty=1,
    order_type=OrderType.MARKET,
    product=ProductType.CNC,
)
order_id = broker.place_order(req)
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
