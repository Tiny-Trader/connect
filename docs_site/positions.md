# Positions

## What is a position
Current net open quantity for an instrument.

## Key points
- positive qty: long
- negative qty: short
- zero qty: closed/flat

## Read open positions
```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    positions = broker.get_positions()
    for p in positions:
        print(
            p.instrument.exchange,
            p.instrument.symbol,
            "qty=", p.qty,
            "avg=", p.avg_price,
            "ltp=", p.ltp,
            "pnl=", p.pnl,
            "product=", p.product,
        )
```

## Close all open positions
```python
with TTConnect("zerodha", config) as broker:
    placed_order_ids, failed_symbols = broker.close_all_positions()
    print("Close orders:", placed_order_ids)
    print("Failed:", failed_symbols)
```

## Suggested check after close
```python
with TTConnect("zerodha", config) as broker:
    still_open = [p for p in broker.get_positions() if p.qty != 0]
    print("Open count after close:", len(still_open))
```

## Caution
close-all sends market actions; always verify product/segment limits.

## See also
- [Client methods (`get_positions`, `close_all_positions`)](reference/clients.md)
- [Models (`Position`)](reference/models.md)
- [Enums (`ProductType`, `Side`)](reference/enums.md)
- [Recipe: Close all open positions](recipes/close-all-open-positions.md)
