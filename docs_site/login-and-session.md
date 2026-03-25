# Login & Session

## Login modes
- Manual: you provide token
- Auto: package logs in and refreshes token (if broker supports)

## Zerodha (manual token)
```python
from tt_connect import TTConnect

config = {
    "api_key": "YOUR_API_KEY",
    "access_token": "YOUR_ACCESS_TOKEN",
}

with TTConnect("zerodha", config) as broker:
    print(broker.get_profile().name)
```

## AngelOne auto mode (TOTP)
```python
from tt_connect import TTConnect

config = {
    "auth_mode": "auto",
    "api_key": "YOUR_API_KEY",
    "client_id": "YOUR_CLIENT_ID",
    "pin": "1234",
    "totp_secret": "BASE32_SECRET",
    "cache_session": True,
}

with TTConnect("angelone", config) as broker:
    print(broker.get_profile().name)
```

## AngelOne manual mode
```python
from tt_connect import TTConnect

config = {
    "auth_mode": "manual",
    "api_key": "YOUR_API_KEY",
    "access_token": "YOUR_JWT_TOKEN",
}

with TTConnect("angelone", config) as broker:
    print(broker.get_profile().name)
```

## Session lifecycle
- Client creation triggers login/init.
- Sessions can be reused within the same trading day.

!!! warning "Daily token expiry (SEBI requirement)"
    All Indian broker tokens expire at end-of-day. This is a SEBI mandate, not a tt-connect limitation. You must re-authenticate each trading day.

    - **Zerodha**: Complete the OAuth login flow daily to get a fresh `access_token`.
    - **AngelOne (auto mode)**: Set `cache_session: True` — tt-connect will auto-login via TOTP and cache the session for the day.
    - **AngelOne (manual mode)**: Obtain a fresh `access_token` JWT daily.

    If your token expires mid-session, API calls will raise `AuthenticationError`.

## Good practices
- keep credentials in env vars/secret manager
- do not hardcode tokens
- always close the client (`with` does this automatically)

## Common issues
- missing API key/token
- expired token
- wrong auth mode for selected broker

## What's next?
- [Config & Environment](config-and-env.md) — all config keys and env var mapping
- [Instruments](instruments.md) — understand what you can trade

## See also
- [Client methods](reference/clients.md)
- [Enums (`AuthMode`)](reference/enums.md)
- [Exceptions](reference/exceptions.md)
- [Broker capabilities](reference/capabilities.md)
- [Troubleshooting: Auth failures](troubleshooting/auth-failures.md)
