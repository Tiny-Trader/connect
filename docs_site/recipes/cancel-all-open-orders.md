# Recipe: Cancel All Open Orders

Use this during risk-off or session cleanup.

```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    cancelled, failed = broker.cancel_all_orders()
    print("Cancelled:", cancelled)
    print("Failed:", failed)
```

## Suggested checks
- Run once and record counts.
- If any failed, fetch `get_orders()` and inspect status/reason.

## What's next?
- [Close all open positions](close-all-open-positions.md) — exit all positions after cancelling orders
- [Safety & Good Practices](../safety-and-good-practices.md) — production checklist

## Related reference
- [Client methods (`cancel_all_orders`, `get_orders`)](../reference/clients.md)
- [Exceptions](../reference/exceptions.md)
- [Troubleshooting: Duplicate orders](../troubleshooting/duplicate-orders.md)
