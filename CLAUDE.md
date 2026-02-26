# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**tt-connect** is a unified Python broker API for Indian stock markets. It provides a single canonical interface across multiple brokers (Zerodha, AngelOne) for authentication, portfolio queries, order management, instrument resolution, and WebSocket streaming.

## Development Commands

All commands assume Poetry is installed and `poetry install` has been run from the `connect/` directory.

```bash
make lint           # ruff style checks
make typecheck      # mypy strict type checking
make test           # full test suite (unit + integration)
make test-fast      # quiet mode test run
make coverage       # tests with 64% minimum coverage gate
make precommit-run  # run all pre-commit hooks manually
```

Run a single test file:
```bash
poetry run pytest tests/unit/test_client.py -v
```

Run a specific test:
```bash
poetry run pytest tests/unit/test_client.py::TestClassName::test_method -v
```

## Architecture

### Core Design Principles

1. **Bidirectional Normalization**: All broker-specific data is translated to/from canonical Python objects. Users never interact with raw broker JSON.
2. **Async-First**: The core (`AsyncTTConnect`) is 100% async. `TTConnect` is a thin synchronous wrapper using a dedicated event loop thread — zero code duplication.
3. **Auto-Registration**: Brokers self-register via `__init_subclass__` in `BrokerAdapter`. No central registry file exists or should be created.
4. **Capability Checking**: Each broker declares a `Capabilities` dataclass. Operations are validated before any network call, raising `UnsupportedFeatureError` for invalid combinations.

### Key Layers

**Public API** (`tt_connect/__init__.py`): Exports only `TTConnect` and `AsyncTTConnect`.

**Client** (`tt_connect/client.py`): `AsyncTTConnect` holds an instantiated `BrokerAdapter`, an `InstrumentManager`, and an optional `BrokerWebSocket`. `TTConnect` wraps it with `_run()` on a background thread's event loop.

**Adapter Layer** (`tt_connect/adapters/`): Each broker has its own subdirectory containing:
- `adapter.py` — HTTP endpoints, inherits `BrokerAdapter`
- `auth.py` — Auth flow, inherits `BaseAuth`
- `transformer.py` — All normalization logic (`to_*` for responses, `to_*_params` for requests, `parse_error` for exception mapping)
- `parser.py` — Instrument master file parsing (CSV for Zerodha, JSON for AngelOne)
- `capabilities.py` — Segments, order types, product types supported

**Instrument Manager** (`tt_connect/instrument_manager/`): Fetches broker instrument master files, parses them, stores in SQLite (`aiosqlite`), and resolves canonical `Instrument` objects to broker-specific tokens. Uses `lru_cache` for hot-path lookups.

**Models/Enums** (`tt_connect/models.py`, `tt_connect/enums.py`): All response models are frozen Pydantic v2 models. Enums (`Exchange`, `OrderType`, `Side`, `ProductType`, `OrderStatus`, `OptionType`) are the canonical vocabulary — never use raw strings where enums exist.

**WebSocket** (`tt_connect/ws/`): `BrokerWebSocket` abstract base; `AngelOne` and `Zerodha` (KiteTicker binary protocol) implementations exist. `normalizer.py` converts raw tick dicts to canonical `Tick` models.

### Adding a New Broker

1. Create `tt_connect/adapters/<broker>/` with `adapter.py`, `auth.py`, `transformer.py`, `parser.py`, `capabilities.py`
2. Subclass `BrokerAdapter` — auto-registration happens via `__init_subclass__`
3. Add test fixtures under `tests/fixtures/<broker>/`
4. Add unit tests in `tests/unit/adapters/<broker>/` and integration tests in `tests/integration/`

## Tech Stack

| Component | Library |
|-----------|---------|
| HTTP | `httpx` (async) |
| Validation | `pydantic` v2 |
| Database | `aiosqlite` + SQLite |
| WebSocket | `websockets` 12+ |
| TOTP | `pyotp` |
| Linting | `ruff` |
| Type checking | `mypy` (strict) |
| Testing | `pytest` + `pytest-asyncio` |
| HTTP mocking | `respx` |
| Time mocking | `freezegun` |

## Tests

- `tests/unit/` — fully isolated, all external calls mocked
- `tests/integration/` — real SQLite DB, mocked HTTP (via `respx`)
- `tests/live/` — manual live broker tests, excluded from CI
- `tests/fixtures/` — static broker response JSON/CSV files used across tests

Minimum coverage gate is 64% (enforced in CI via `make coverage`).

## CI/CD

Three GitHub Actions workflows in `.github/workflows/`:
- `connect-ci.yml` — lint, typecheck, test, coverage on every PR/push
- `release.yml` — package build and publish on release tags
- `changelog-check.yml` — enforces CHANGELOG.md updates on PRs

Python version in CI: **3.11**.
