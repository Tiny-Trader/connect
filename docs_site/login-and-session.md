# Login & Session

## Login modes
- Manual: you provide token
- Auto: package logs in and refreshes token (if broker supports)

## Session lifecycle
- `create client` -> login happens
- session is reused while valid
- session expires per broker rules

## What users should do
- keep credentials in env vars or secret manager
- close client cleanly on shutdown
- handle auth errors explicitly

## Common issues
- missing API key/token
- expired token
- wrong auth mode for selected broker
