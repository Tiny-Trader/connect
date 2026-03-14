# Changelog

## 0.7.0 - 2026-03-14

- Bump: **minor**
- Source PR: #46 feat(ws): uniform feed health across all brokers

### Added

- **Feed health observability** — both Zerodha and AngelOne now expose identical feed-health
  machinery. New public API on `AsyncTTConnect`:
  - `broker.feed_state` — returns a `FeedState` enum value: `CONNECTING`, `CONNECTED`,
    `STALE`, `RECONNECTING`, or `CLOSED`
  - `broker.last_tick_at(instrument)` — IST wall-clock time of the last tick received for
    a specific instrument, or `None` if no tick has arrived yet
- **`on_stale` / `on_recovered` callbacks** — `subscribe()` now accepts two optional async
  callbacks. `on_stale` fires when no tick is received for 30 seconds; `on_recovered` fires
  on the first tick after a stale period. Both work identically across brokers and survive
  reconnects.
- **`FeedState` enum** — importable from `tt_connect.enums`.

### Changed

- `BrokerWebSocket` base class now contains all shared lifecycle and feed-health logic
  (reconnect loop, staleness detection, `_record_tick`, `_staleness_loop`). Broker
  subclasses implement only the broker-specific hooks (binary parsing, auth headers,
  ping mechanism). No public API change.
- Zerodha WebSocket now has full feed-health parity with AngelOne: staleness detection,
  `on_stale` / `on_recovered` callbacks, and `feed_state` / `last_tick_at` work on
  Zerodha subscriptions as well.
- AngelOne WebSocket: replaced `_ping_loop` with the shared `_staleness_loop` from the
  base class. Behaviour is unchanged — text `"ping"` frames are still sent every 10 seconds.
- Fixed AngelOne WebSocket disconnect loop in production caused by `websockets` library
  ping/pong (RFC 6455 binary frames) conflicting with AngelOne's application-level text
  `"ping"` frames. Disabled library ping with `ping_interval=None`.


## 0.6.1 - 2026-03-13

- Bump: **patch**
- Source PR: #45 feat: enforce IST-aware datetimes across all broker surfaces

### Changed

- All datetime fields across the public API are now **IST-aware** (`UTC+05:30`).
  A shared `IST` constant and `ISTDatetime` Pydantic type live in
  `tt_connect.core.timezone`. Naive datetimes are assumed to be IST (no user
  code change required); any other timezone-aware datetime is normalised to IST.
  Affected surfaces:
  - `Order.timestamp`, `Trade.timestamp`, `Tick.timestamp`, `Candle.timestamp`
  - `get_historical` `from_date` / `to_date` inputs
  - WebSocket ticks (both Zerodha and AngelOne)
  - Auth session fields (`obtained_at`, `expires_at`)


## 0.6.0 - 2026-03-12

- Bump: **minor**
- Source PR: #44 feat: add public instrument store discovery surface

### Added

- Added stable public import modules for instruments, enums, and exceptions so the strict
  typed API can be imported through `tt_connect.instruments`, `tt_connect.enums`, and
  `tt_connect.exceptions`.
- Added a public local `InstrumentStore` / `AsyncInstrumentStore` discovery surface over
  the broker instrument cache, while keeping broker auth and daily refresh ownership with
  `TTConnect` / `AsyncTTConnect`.

### Changed

- Refactored store internals to separate refresh lifecycle from read-only discovery queries,
  and consolidated store-side flat list lookups under `list_instruments(...)` with strict
  canonical filters.


## 0.5.1 - 2026-03-12

- Bump: **patch**
- Source PR: #43 Fix/apache license trademark

### Changed

- Switched the project license from AGPL to Apache License 2.0.
- Added explicit `Apache-2.0` package metadata in `pyproject.toml`.
- Updated compliance guidance to clarify Apache-2.0 redistribution obligations, including
  license/attribution preservation on redistributed source or binaries, and that it does
  not require publishing source code for network or hosted use.
- Tightened trademark policy to protect `Tiny Traders`, `TT`, and `tt-connect` branding
  while keeping code reuse permissive under Apache-2.0.


## 0.5.0 - 2026-03-11

- Bump: **minor**
- Source PR: #42 refactor(api): flatten public order/GTT methods to accept kwargs

### Changed

- **Breaking: public order/GTT methods now accept keyword arguments instead of request objects.**
  `place_order`, `modify_order`, `place_gtt`, and `modify_gtt` on both `AsyncTTConnect` and `TTConnect`
  no longer accept a single request-object argument. Pass fields directly as keyword arguments:

  ```python
  # Before (0.4.x)
  broker.place_order(PlaceOrderRequest(instrument=..., side=Side.BUY, qty=1, ...))

  # After (0.5.0+)
  broker.place_order(instrument=..., side=Side.BUY, qty=1, ...)
  ```

- **`PlaceOrderRequest`, `ModifyOrderRequest`, `PlaceGttRequest`, `ModifyGttRequest`,
  and `GetHistoricalRequest` removed from the public package exports.**
  These were internal DTOs accidentally exposed. They remain in `tt_connect.core.models.requests`
  for internal use; user code should not import them.
  `GttLeg` stays exported — it is a value type users compose directly for GTT legs.

### Migration

```python
# place_order
# was: broker.place_order(PlaceOrderRequest(instrument=eq, side=Side.BUY, qty=10, ...))
broker.place_order(instrument=eq, side=Side.BUY, qty=10,
                   order_type=OrderType.MARKET, product=ProductType.CNC)

# modify_order
# was: broker.modify_order(ModifyOrderRequest(order_id="O1", price=801.0))
broker.modify_order(order_id="O1", price=801.0)

# place_gtt
# was: broker.place_gtt(PlaceGttRequest(instrument=eq, last_price=2800.0, legs=[...]))
broker.place_gtt(instrument=eq, last_price=2800.0, legs=[GttLeg(...)])

# modify_gtt
# was: broker.modify_gtt(ModifyGttRequest(gtt_id="G1", instrument=eq, last_price=2800.0, legs=[...]))
broker.modify_gtt(gtt_id="G1", instrument=eq, last_price=2800.0, legs=[GttLeg(...)])
```


## 0.4.8 - 2026-03-05

- Bump: **patch**
- Source PR: #40 ci(docs): fix mkdocs extensions in CI and Pages


## 0.4.7 - 2026-03-05

- Bump: **patch**
- Source PR: #38 docs(mkdocs): recover docs site and add GitHub Pages deploy


## 0.4.6 - 2026-03-05

- Bump: **patch**
- Source PR: #37 ci(release): fix pypi deployment status tracking


## 0.4.5 - 2026-03-05

- Bump: **patch**
- Source PR: #35 Chore/readme badges


## 0.4.4 - 2026-03-05

- Bump: **patch**
- Source PR: #34 Chore/add docstrings


## 0.4.3 - 2026-03-05

- Bump: **patch**
- Source PR: #33 Chore/add docstrings


## 0.4.2 - 2026-03-05

- Bump: **patch**
- Source PR: #32 Chore/release pr template dev main


## 0.4.1 - 2026-03-05

- Bump: **patch**
- Source PR: #31 Feat/upgrade logging observability


## 0.4.0 - 2026-03-04

- Bump: **minor**
- Source PR: #29 Feat/restructure core brokers

### Changed

- **Architecture: `core/` + `brokers/` restructure.** The entire package has been reorganized
  into two top-level directories with clean separation of concerns:
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
  - Updated `README.md` with badges for CI status, PyPI version, supported Python versions, and license.
- Release workflow deployment tracking:
  - Updated `.github/workflows/publish-main.yml` to publish under GitHub environment `pypi` so deployment status reflects current releases.
- MkDocs documentation recovery:
  - Reintroduced `mkdocs.yml` and `docs_site/` content on top of current `dev`.
  - Added `docs_check` CI job in `.github/workflows/connect-ci.yml` for strict MkDocs builds.
  - Added `make docs-serve` and `make docs-build` targets in `Makefile`.
  - Simplified docs theme to built-in `readthedocs` and removed custom theme assets/styles for a clean baseline.
  - Added `.github/workflows/docs-pages.yml` to deploy docs to GitHub Pages from `main`.
  - Fixed docs CI/Pages dependencies by installing `pymdown-extensions` where MkDocs runs.
  - Updated repository README and About metadata with live docs/PyPI links and project summary.


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


## 0.1.0 - 2026-02-22

### Added

- Initial `tt-connect` package with unified broker abstraction for Indian markets.
- Zerodha and AngelOne adapter foundations.
- Canonical models/enums, instrument manager, and resolver.
- Unit and integration test suites with CI lint/type/test gates.
