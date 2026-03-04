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
