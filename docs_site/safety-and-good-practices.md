# Safety & Good Practices

## Before placing orders
- validate instrument and quantity
- check available funds
- check market state/session

## Pre-order safety check example
```python
from tt_connect import TTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    funds = broker.get_funds()
    if funds.available < 1000:
        raise RuntimeError("Not enough funds for this strategy")

    order_id = broker.place_order(
        instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
        side=Side.BUY,
        qty=1,
        order_type=OrderType.MARKET,
        product=ProductType.CNC,
    )
    print("placed:", order_id)
```

## Logging
- log order request id, order id, status changes
- keep enough data for audit/replay

## Secrets
- never hardcode tokens
- use env vars or secret manager
- rotate credentials on leaks

## Basic error guard example
```python
from tt_connect.exceptions import TTConnectError, AuthenticationError

try:
    profile = broker.get_profile()
except AuthenticationError:
    # trigger re-auth flow
    raise
except TTConnectError as e:
    # alert + log for ops
    print("tt-connect error:", e)
    raise
```

## Production checklist
- retry policy configured
- alerts for auth/placement failures
- graceful shutdown closes client
- risk-off path tested (`cancel_all_orders`, `close_all_positions`)

## See also
- [Errors & retries](errors-and-retries.md)
- [Exceptions](reference/exceptions.md)
- [Broker capabilities](reference/capabilities.md)
- [Recipe: Close all open positions](recipes/close-all-open-positions.md)
