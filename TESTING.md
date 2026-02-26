# tt-connect — Testing Guide

This document describes the current automated and manual testing setup.

## Scope

- Automated CI scope: `tests/unit` + `tests/integration`
- Manual scope: `tests/live`
- Current collection baseline: `256 tests collected` (from `pytest --collect-only` on February 27, 2026)

## Commands

```bash
# Fast local run (same scope as CI)
make test-fast

# Full local run including live tests (requires credentials/network)
make test

# Coverage gate (unit + integration)
make coverage
```

Equivalent direct commands:

```bash
poetry run pytest -q tests/unit tests/integration
poetry run pytest tests/unit tests/integration --cov=tt_connect --cov-report=xml --cov-fail-under=64
```

## Test Layout

```text
tests/
├── unit/                # no real broker network; fast logic-level tests
├── integration/         # in-memory SQLite + mocked broker interactions
├── live/                # real broker credentials + network; not part of CI
├── fixtures/
│   ├── zerodha_instruments.csv
│   └── responses/zerodha/*.json
├── test_capabilities.py
└── test_zerodha_auth.py
```

## What Each Tier Validates

- Unit tests:
  - enums, config validation, models
  - transformer mappings (Zerodha + AngelOne)
  - websocket packet normalization/handling
  - mixin behavior (`orders`, `portfolio`, sync wrapper)
  - idempotency tag behavior

- Integration tests:
  - instrument manager refresh/insert pipeline
  - resolver correctness for index/equity/future/option
  - async client init/lifecycle wiring with realistic dependencies

- Live tests:
  - credentialed smoke checks against real broker APIs
  - use [`tests/live/README.md`](./tests/live/README.md) for setup

## CI Expectations

Required checks for PRs are defined in [`CONTRIBUTING.md`](./CONTRIBUTING.md):

- lint (`ruff`)
- type check (`mypy`)
- unit + integration tests (`pytest`)
- coverage threshold (`>=64%`)
- package build (`poetry build`)

Live tests are intentionally excluded from required CI.

## Notes

- Keep fixtures deterministic and minimal.
- Prefer unit tests first; add integration tests for DB/lifecycle behavior.
- If behavior changes are user-visible, update [`CHANGELOG.md`](./CHANGELOG.md) in the same PR.
