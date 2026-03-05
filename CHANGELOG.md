# Changelog

## 0.4.2 - 2026-03-05

- Bump: **patch**
- Source PR: #32 Chore/release pr template dev main


## 0.4.1 - 2026-03-05

- Bump: **patch**
- Source PR: #31 Feat/upgrade logging observability


## 0.4.0 - 2026-03-04

- Bump: **minor**
- Source PR: #29 Feat/restructure core brokers


## 0.4.0 - 2026-03-05

- Bump: **minor**

### Changed

- **Architecture: `core/` + `brokers/` restructure.** The entire package has been reorganized into two top-level directories with clean separation of concerns:
  - `core/client/` — public API (`AsyncTTConnect`, `TTConnect`) with private mixin files.
  - `core/models/` — all data types split by lifecycle direction (`enums`, `instruments`, `requests`, `responses`, `config`).
  - `core/adapter/` — full broker SPI (`BrokerAdapter`, `BrokerTransformer` Protocol, `BaseAuth`, `BrokerWebSocket`, `Capabilities`).
  - `core/store/` — SQLite-backed instrument management and resolution.
  - `brokers/zerodha/` and `brokers/angelone/` — fully self-contained per broker (adapter, auth, config, transformer, parser, ws, capabilities).
- **Auto-discovery replaces hardcoded imports.** `brokers/__init__.py` uses `pkgutil.iter_modules` — adding a broker no longer requires editing `__init__.py`.
- **Config auto-registration via `__init_subclass__`.** Each broker's config class self-registers, replacing the hardcoded `_CONFIG_MODELS` dict.
- **WebSocket clients moved into broker folders.** `ws/zerodha.py` → `brokers/zerodha/ws.py`, `ws/angelone.py` → `brokers/angelone/ws.py`.
- **Auth base + stores merged** into a single `core/adapter/auth.py`.
- **`models.py` split** into `requests.py` (what users send) and `responses.py` (what comes back).

### Migration

- All public imports from `tt_connect` remain unchanged — no user-facing API break.
- Internal imports changed from `tt_connect.enums` → `tt_connect.core.models.enums`, etc.

## 0.3.0 - 2026-03-01

- Bump: **minor**
- Source PR: #27 feat(core): add logging

## [Unreleased]

### Added

- Structured JSON logging via `setup_logging()` (opt-in, zero new dependencies).
  - `TTConnectJsonFormatter` emits one JSON line per record with stable fields: `ts`, `level`, `logger`, `message`, plus any caller-supplied `extra` fields merged in.
  - 27 named events across auth, HTTP, instrument refresh, client lifecycle, and WebSocket layers (e.g. `auth.login`, `request.end`, `ws.connect`).
  - `setup_logging(level="INFO", fmt="json"|"text")` exported from the top-level package.
  - Library remains silent by default (`NullHandler`) — existing users see no change.
- Usage demonstrated in `examples/zerodha.py` and `examples/angelone.py`.
- PR workflow templates for releases:
  - Added `.github/PULL_REQUEST_TEMPLATE/release-dev-to-main.md` for `dev -> main` release PRs.
  - Updated `.github/pull_request_template.md` to point release PRs to the dedicated release template.
- Upgrade-aware package-level observability events:
  - One-time startup event: `package.startup` with `tt_connect_version`, broker, auth mode, stale policy, and session cache mode.
  - One-time migration hints: `upgrade.notice` for deprecated config key names (e.g. `authMode` -> `auth_mode`, `apiKey` -> `api_key`).
  - Automatic emission during client initialization (no application code changes required).
- Documentation additions:
  - Added `docs/CORE_BROKER_INTEGRATION.md` to explain `core/` ↔ `brokers/` integration, registries, lifecycle, order flow, and streaming flow.
  - Added `docs/REMAINING_WORK.md` to track open issues, docs gaps, design limitations, and roadmap priorities.

## 0.2.4 - 2026-02-28

- Bump: **patch**
- Source PR: #26 fix(brokers): update the subscription mode for ws

## 0.2.3 - 2026-02-28

- Bump: **patch**
- Source PR: #25 ci(docs): remove legacy release workflow and align pipeline docs

## 0.2.2 - 2026-02-28

- Bump: **patch**
- Source PR: #24 ci(release): fix fallback PR lookup regex

## 0.2.1 - 2026-02-28

- Bump: **patch**
- Source PR: #19 ci(release): harden dev merge PR detection for auto-bump

## 0.2.0 - 2026-02-28

- Bump: **minor**
- Source PR: #17 feat: add instrument helper APIs (futures/options/expiries/search)

## 0.1.1 - 2026-02-28

- Bump: **patch**
- Source PR: #16 ci(release): fix auth precedence for dev auto-bump push

## [0.1.0] - 2026-02-22

### Added

- Initial `tt-connect` package with unified broker abstraction for Indian markets.
- Zerodha and AngelOne adapter foundations.
- Canonical models/enums, instrument manager, and resolver.
- Unit and integration test suites with CI lint/type/test gates.
