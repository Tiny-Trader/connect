# Changelog

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


All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Instrument helper APIs for discovery and contract lookup: `search_instruments`, `get_futures`, `get_options`, and `get_expiries`.
- Facade hardening for client internals to reduce accidental use of private attributes and methods.
- Zerodha WebSocket streaming via KiteTicker binary protocol — `subscribe()` now works on both Zerodha and AngelOne.
- GTT (Good Till Triggered) orders for both brokers: `place_gtt`, `modify_gtt`, `cancel_gtt`, `get_gtt`, `get_gtts`. Zerodha supports two-leg OCO; AngelOne supports single-leg.
- New canonical models: `PlaceGttRequest`, `ModifyGttRequest`, `GttLeg`, `Gtt`.
- Elegance refactor: explicit `ClientState` state machine, mixin decomposition (`LifecycleMixin`, `PortfolioMixin`, `OrdersMixin`), `PlaceOrderRequest`/`ModifyOrderRequest` request objects, and context manager support (`async with` / `with`).
- Release governance docs and automation:
  - `RELEASE.md`
  - changelog validation workflow
  - tag-driven publish workflow

## [0.1.0] - 2026-02-22

### Added
- Initial `tt-connect` package with unified broker abstraction for Indian markets.
- Zerodha and AngelOne adapter foundations.
- Canonical models/enums, instrument manager, and resolver.
- Unit and integration test suites with CI lint/type/test gates.
