# Changelog

## [Unreleased]

### Added
- Structured JSON logging via `setup_logging()` (opt-in, zero new dependencies).
  - `TTConnectJsonFormatter` emits one JSON line per record with stable fields: `ts`, `level`, `logger`, `message`, plus any caller-supplied `extra` fields merged in.
  - 27 named events across auth, HTTP, instrument refresh, client lifecycle, and WebSocket layers (e.g. `auth.login`, `request.end`, `ws.connect`).
  - `setup_logging(level="INFO", fmt="json"|"text")` exported from the top-level package.
  - Library remains silent by default (`NullHandler`) — existing users see no change.
- Usage demonstrated in `examples/zerodha.py` and `examples/angelone.py`.

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
