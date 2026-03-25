# Recipe: Close All Open Positions

This places offsetting market actions for open positions.

```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    placed_order_ids, failed_symbols = broker.close_all_positions()
    print("Placed close orders:", placed_order_ids)
    print("Failed symbols:", failed_symbols)
```

## Important
- This is a high-impact action.
- Verify open positions before and after.
- Run in controlled environments first.

## What's next?
- [Cancel all open orders](cancel-all-open-orders.md) — cancel pending orders before closing positions
- [Errors & Retries](../errors-and-retries.md) — handle partial failures gracefully

## Related reference
- [Client methods (`get_positions`, `close_all_positions`)](../reference/clients.md)
- [Models (`Position`)](../reference/models.md)
- [Safety & Good Practices](../safety-and-good-practices.md)
