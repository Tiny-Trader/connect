# Errors & Retries

## Common error types
```python
from tt_connect.exceptions import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
    UnsupportedFeatureError,
    InsufficientFundsError,
    BrokerError,
    TTConnectError,
)
```

## Basic handling pattern
```python
try:
    order_id = broker.place_order(instrument=..., side=..., qty=1, order_type=..., product=...)
except InsufficientFundsError:
    # do not retry; change size/funds first
    raise
except UnsupportedFeatureError:
    # do not retry; broker does not support this flow
    raise
except RateLimitError:
    # retry with backoff
    raise
except AuthenticationError:
    # refresh/re-login flow
    raise
except BrokerError:
    # broker rejected request; inspect message
    raise
except TTConnectError:
    # generic library-level error fallback
    raise
```

## Retry guidance
Retry (with backoff):
- timeout/network transient failures
- rate-limit failures

Do not retry blindly:
- validation/config errors
- insufficient funds
- unsupported feature

## Safe retry idea for place order
- pass a `tag` kwarg to `place_order` for request correlation
- before placing again, check recent orders to avoid duplicates

## See also
- [Exceptions](reference/exceptions.md)
- [Models](reference/models.md)
- [Client methods (orders)](reference/clients.md)
- [Recipe: Cancel all open orders](recipes/cancel-all-open-orders.md)
- [Troubleshooting: Auth failures](troubleshooting/auth-failures.md)
- [Troubleshooting: Order rejected](troubleshooting/order-rejected.md)
- [Troubleshooting: Duplicate orders](troubleshooting/duplicate-orders.md)
