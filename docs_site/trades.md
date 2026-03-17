# Trades

## What is a trade
A trade is an executed fill of an order.

## Important behavior
- one order can create many trades (partial fills)
- avg price is computed from fills
- trade timestamps are broker-provided

## Read trades
```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    trades = broker.get_trades()
    for t in trades:
        print(
            t.order_id,
            t.instrument.symbol,
            t.side,
            "qty=", t.qty,
            "avg=", t.avg_price,
            "value=", t.trade_value,
            "ts=", t.timestamp,
        )
```

## Usage
- use trades for execution reports
- reconcile trades with final order status
- one order may appear in multiple trade entries if partially filled

## See also
- [Client methods (`get_trades`)](reference/clients.md)
- [Models (`Trade`, `Order`)](reference/models.md)
- [Enums (`Side`, `OrderStatus`)](reference/enums.md)
