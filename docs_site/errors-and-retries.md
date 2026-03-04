# Errors & Retries

## Error groups
- auth errors
- validation/config errors
- broker/business errors
- timeout/network errors
- unsupported feature errors

## Retry guidance
Retry:
- timeout/network transient failures
- rate-limit failures with backoff

Do not retry blindly:
- bad request/validation errors
- insufficient funds
- unsupported feature

## Safe retry pattern
- attach unique client tag/idempotency key when possible
- check order book before re-sending place order
