# Exceptions

## Exception table

| Exception | When it happens | Retryable |
|---|---|---|
| `TTConnectError` | Base library error type | No |
| `AuthenticationError` | Invalid/expired auth, login/session issues | No |
| `ConfigurationError` | Missing/invalid config values | No |
| `UnsupportedFeatureError` | Broker does not support requested operation | No |
| `InstrumentNotFoundError` | Instrument could not be resolved from local master | No |
| `InstrumentManagerError` | Instrument manager not initialized correctly | No |
| `BrokerError` | Generic broker-side failure response | No |
| `OrderError` | Base order error class | No |
| `InvalidOrderError` | Order payload/params invalid | No |
| `OrderNotFoundError` | Order ID not found | No |
| `InsufficientFundsError` | Not enough funds/margin | No |
| `RateLimitError` | Broker/API rate-limit exceeded | Yes |
| `ClientNotConnectedError` | Method called before init/connect | No |
| `ClientClosedError` | Method called after client closed | No |

## Handling pattern
- Catch specific errors first (`InsufficientFundsError`, `RateLimitError`, `AuthenticationError`).
- Use `TTConnectError` as final fallback.
- Retry only when it is clearly transient (for example `RateLimitError`).

## Related guides
- [Errors & Retries](../errors-and-retries.md)
- [Login & Session](../login-and-session.md)
- [Safety & Good Practices](../safety-and-good-practices.md)
