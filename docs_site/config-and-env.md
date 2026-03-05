# Config & Environment Variables

This page shows all config keys you should set for each broker.

## Common config keys

| Key | Type | Default | Used for |
|---|---|---|---|
| `on_stale` | `"fail" | "warn"` | `"fail"` | Instrument cache refresh behavior |
| `cache_session` | `bool` | `False` | Persist session for reuse |

## `on_stale` behavior

| Value | Meaning |
|---|---|
| `fail` | If instrument refresh fails, client init fails |
| `warn` | If refresh fails and cache exists, continue with stale cache |

## Zerodha config

### Required keys

| Key | Required | Notes |
|---|---|---|
| `api_key` | Yes | Kite app API key |
| `access_token` | Yes | Daily token from Zerodha login flow |

### Optional keys

| Key | Required | Notes |
|---|---|---|
| `on_stale` | No | `"fail"` or `"warn"` |
| `cache_session` | No | Session caching toggle |

### Example (dict)
```python
config = {
    "api_key": "YOUR_ZERODHA_API_KEY",
    "access_token": "YOUR_ZERODHA_ACCESS_TOKEN",
    "on_stale": "fail",
    "cache_session": False,
}
```

## AngelOne config

### Manual mode (`auth_mode = "manual"`)

| Key | Required | Notes |
|---|---|---|
| `auth_mode` | Yes | Set to `"manual"` |
| `api_key` | Yes | SmartAPI app key |
| `access_token` | Yes | JWT access token |
| `on_stale` | No | `"fail"` or `"warn"` |
| `cache_session` | No | Session caching toggle |

### Auto mode (`auth_mode = "auto"`)

| Key | Required | Notes |
|---|---|---|
| `auth_mode` | Yes | Set to `"auto"` |
| `api_key` | Yes | SmartAPI app key |
| `client_id` | Yes | AngelOne client code |
| `pin` | Yes | Trading PIN |
| `totp_secret` | Yes | Base32 TOTP secret |
| `on_stale` | No | `"fail"` or `"warn"` |
| `cache_session` | No | Useful in auto mode |

### Example (auto mode)
```python
config = {
    "auth_mode": "auto",
    "api_key": "YOUR_ANGELONE_API_KEY",
    "client_id": "YOUR_CLIENT_ID",
    "pin": "1234",
    "totp_secret": "BASE32_SECRET",
    "cache_session": True,
    "on_stale": "warn",
}
```

## Environment variable mapping

| Config key | Environment variable |
|---|---|
| `api_key` (Zerodha) | `ZERODHA_API_KEY` |
| `access_token` (Zerodha) | `ZERODHA_ACCESS_TOKEN` |
| `api_key` (AngelOne) | `ANGELONE_API_KEY` |
| `access_token` (AngelOne manual) | `ANGELONE_ACCESS_TOKEN` |
| `client_id` (AngelOne auto) | `ANGELONE_CLIENT_ID` |
| `pin` (AngelOne auto) | `ANGELONE_PIN` |
| `totp_secret` (AngelOne auto) | `ANGELONE_TOTP_SECRET` |

## Example: from env vars
```python
import os
from tt_connect import TTConnect

config = {
    "api_key": os.environ["ZERODHA_API_KEY"],
    "access_token": os.environ["ZERODHA_ACCESS_TOKEN"],
}

with TTConnect("zerodha", config) as broker:
    print(broker.get_profile().name)
```

## Common config mistakes
- using `auto` auth mode on a broker that supports only manual
- missing `totp_secret` in AngelOne auto mode
- using expired access token
- mixing environment variables from different brokers

## Related
- [Login & Session](login-and-session.md)
- [Troubleshooting: Auth failures](troubleshooting/auth-failures.md)
- [Broker capabilities](reference/capabilities.md)
