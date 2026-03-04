# Safety & Good Practices

## Before placing orders
- validate instrument and quantity
- check available funds
- check market state/session

## Logging
- log order request id, order id, status changes
- keep enough data for audit/replay

## Secrets
- never hardcode tokens
- use env vars or secret manager
- rotate credentials on leaks

## Production checklist
- retry policy configured
- alerts for auth/placement failures
- graceful shutdown closes client

## See also
- [Errors & retries](errors-and-retries.md)
- [Exceptions](reference/exceptions.md)
- [Broker capabilities](reference/capabilities.md)
- [Recipe: Close all open positions](recipes/close-all-open-positions.md)
