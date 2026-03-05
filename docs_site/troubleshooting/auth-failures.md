# Auth Failures

## Common symptoms
- `AuthenticationError`
- profile/funds call fails right after startup
- token works in one session but fails in another

## Fast checks
1. Confirm broker id is correct (`zerodha` or `angelone`).
2. Confirm required config keys are present.
3. Confirm token/session is still valid.
4. Confirm auth mode is supported by broker.

## Minimal test
```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    print(broker.get_profile())
```

## Broker-specific notes
- Zerodha: manual token flow only.
- AngelOne: supports manual and auto; auto needs `client_id`, `pin`, `totp_secret`.

## What to do next
- refresh/recreate token
- verify system clock and TOTP secret for auto login
- turn off stale cached session and retry

## Related
- [Login & Session](../login-and-session.md)
- [Config & Environment](../config-and-env.md)
- [Exceptions](../reference/exceptions.md)
- [Broker operation notes](../reference/operation-notes.md)
