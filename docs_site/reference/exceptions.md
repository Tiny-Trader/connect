# Exceptions

## Base type
- `TTConnectError(message, broker_code=None)`

## Auth / config
- `AuthenticationError`
- `ConfigurationError`

## Feature / data
- `UnsupportedFeatureError`
- `InstrumentNotFoundError`
- `InstrumentManagerError`

## Order / broker
- `BrokerError`
- `OrderError`
- `InvalidOrderError`
- `OrderNotFoundError`
- `InsufficientFundsError`
- `RateLimitError`

## Client lifecycle
- `ClientNotConnectedError`
- `ClientClosedError`

## Retry note
Only `RateLimitError` is marked retryable in the exception hierarchy.

## Related guides
- [Errors & Retries](../errors-and-retries.md)
- [Login & Session](../login-and-session.md)
- [Safety & Good Practices](../safety-and-good-practices.md)
