# Contributor Guide

This guide is for developers changing core library behavior, adapters, and tests.

## Local Setup

```bash
cd connect
poetry install
make lint
make typecheck
make test-fast
```

## Project Areas

- `tt_connect/client.py`: public sync/async client API.
- `tt_connect/adapters/`: broker-specific HTTP/auth/transform logic.
- `tt_connect/instrument_manager/`: SQLite master lifecycle + resolver.
- `tests/unit`: pure logic tests (no IO).
- `tests/integration`: in-memory SQLite + mocked HTTP.
- `tests/live`: manual credentialed tests (not required in CI).

## Development Workflow

1. Branch from `main`: `feat/<topic>` or `fix/<topic>`.
2. Make focused changes with tests.
3. Run `make ci` locally when possible.
4. Update `CHANGELOG.md` for user-visible behavior/API changes.
5. Open PR to `main` with test evidence and risk notes.

## Testing Expectations

- New pure functions: add unit tests.
- DB/query/lifecycle changes: add integration tests.
- Broker behavior changes: update fixture coverage; add/update live tests if needed.

## Style and Quality Gates

- Lint: `ruff`
- Types: strict `mypy`
- Tests: `pytest` (unit + integration)
- Coverage gate in CI (`make coverage`)

## Release-Related Changes

If your PR affects release behavior or user-facing functionality:

1. Update `CHANGELOG.md` under `Unreleased`.
2. Ensure versioning/release implications are clear in PR notes.
3. Follow [../RELEASE.md](../RELEASE.md) for tag and publish policy.
