# tt-connect

Unified Python API layer for Indian brokers. `tt-connect` lets trading apps use one canonical interface for auth, instruments, orders, portfolio, and reports while broker-specific logic stays inside adapters.

## Current Status (as of 2026-02-22)

### Core
- Async-first client (`AsyncTTConnect`) with sync wrapper (`TTConnect`) is implemented.
- Canonical models/enums are in place (Pydantic v2 + strict typing).
- Instrument master pipeline and SQLite-backed resolver are implemented.

### Broker Support Matrix
| Capability | Zerodha | AngelOne |
|---|---|---|
| Auth (manual/auto modes) | Manual | Manual + Auto |
| Profile/Funds/Holdings/Positions | Yes | Yes |
| Orders (place/modify/cancel/list) | Yes | Yes |
| Trades | Yes | Yes |
| Instrument fetch + resolve | Yes | Yes |
| WebSocket streaming | Not implemented yet | In progress |
| Margin calculator API | Planned | Planned |

### Test Status
- `poetry run pytest tests/unit tests/integration` passes locally.
- Live tests are manual (`tests/live/`) and credential-gated.
- Default `pytest` discovery is configured for unit + integration only.

## Quick Start

```bash
cd connect
poetry install
poetry run pytest
poetry run ruff check .
poetry run mypy tt_connect/
```
