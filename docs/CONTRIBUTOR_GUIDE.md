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

- `tt_connect/lifecycle.py`: client state machine, init/close, context managers, WebSocket subscribe.
- `tt_connect/portfolio.py`: read-only portfolio and account queries.
- `tt_connect/orders.py`: order placement, modification, cancellation, position closing.
- `tt_connect/sync_client.py`: `TTConnect` — threaded sync wrapper over `AsyncTTConnect`.
- `tt_connect/client.py`: `AsyncTTConnect` — thin mixin composition (~20 lines).
- `tt_connect/models.py`: all Pydantic models — response models (frozen) and request models (`PlaceOrderRequest`, `ModifyOrderRequest`, `PlaceGttRequest`, `ModifyGttRequest`).
- `tt_connect/adapters/`: broker-specific HTTP/auth/transform logic.
- `tt_connect/instrument_manager/`: SQLite master lifecycle + resolver.
- `tests/unit`: pure logic tests (no IO).
- `tests/integration`: in-memory SQLite + mocked HTTP.
- `tests/live`: manual credentialed tests (not required in CI).

## Development Workflow

1. Branch from `dev`: `feat/<topic>` or `fix/<topic>` (use `hotfix/<topic>` from `main` only for urgent production fixes).
2. Make focused changes with tests.
3. Run `make ci` locally when possible.
4. Update `CHANGELOG.md` for code-impacting changes.
5. Add exactly one semver label for PRs targeting `dev`: `semver:major|semver:minor|semver:patch`.
6. Open PR to `dev` with test evidence and risk notes.
7. Release promotion is done by merging `dev` to `main`, then tagging on `main` as `vX.Y.Z`.

## Testing Expectations

- New pure functions: add unit tests.
- DB/query/lifecycle changes: add integration tests.
- Broker behavior changes: update fixture coverage; add/update live tests if needed.
- When writing integration tests that bypass `init()`, set `broker._state = ClientState.CONNECTED` after manually wiring `_conn` and `_resolver` — otherwise `_require_connected()` will reject the call.

## Style and Quality Gates

- Lint: `ruff`
- Types: strict `mypy`
- Tests: `pytest` (unit + integration)
- Coverage gate in CI (`make coverage`)

## Adding a New Broker

1. Create `tt_connect/adapters/<broker>/` with 5 files:
   - `adapter.py` — subclass `BrokerAdapter(broker_id="<name>")`, implement all abstract methods
   - `auth.py` — login, token refresh, session handling
   - `transformer.py` — implement `to_order_params(token, broker_symbol, exchange, req: PlaceOrderRequest)`, `to_modify_params(req: ModifyOrderRequest)`, and all `to_*` response methods
   - `parser.py` — instrument master file parsing (CSV, JSON, etc.)
   - `capabilities.py` — declare supported segments, order types, product types
2. Add test fixtures under `tests/fixtures/<broker>/`
3. Add unit tests in `tests/unit/adapters/<broker>/`
4. Add integration tests in `tests/integration/`
5. Touch nothing in `client.py`, `lifecycle.py`, `portfolio.py`, or `orders.py`

## Release-Related Changes

If your PR affects release behavior or user-facing functionality:

1. Update `CHANGELOG.md` (for code-impacting changes, this is required by CI).
2. Ensure versioning/release implications are clear in PR notes.
3. Follow [RELEASE_VERSIONING.md](./RELEASE_VERSIONING.md) for tag and publish policy.
