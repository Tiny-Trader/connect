# Changelog

## [Unreleased]

## [0.8.4] - 2026-03-25

### Fixed

- **AngelOne GTT validation (#9)** — `to_gtt_params` / `to_modify_gtt_params` now raise
  `InvalidOrderError` if legs != 1 (was: blind `legs[0]` access causing IndexError on empty
  list, silent truncation on multi-leg).
- **Zerodha GTT validation (#10)** — `to_gtt_params` / `to_modify_gtt_params` now raise
  `InvalidOrderError` if legs not in [1, 2] (was: 0 or 3+ legs silently accepted).
- **AngelOne GTT pagination (#8)** — `get_gtts()` now paginates through all pages
  (was: hardcoded to page 1 with count=50, silently dropping rules beyond 50).
- Removed dead `dev/get_token.py` references; pointed to `TROUBLESHOOTING.md` instead.
- Unified install instructions to `pip install tt-connect` across all examples.

### Docs

- Clarified sync/async client API parity — `subscribe`/`unsubscribe` are async-only.
- Clarified `cache_session` vs `auth_mode=auto` — `cache_session` controls disk persistence, not auto-login eligibility.
- Added InstrumentStore API reference, broker-specific warnings, and cross-navigation links.
- Added SEBI daily token expiry warning with per-broker details.

## [0.8.0] - 2026-03-18

### Added

- **`Order.instrument` now populated** — `get_orders()` and `get_order()` previously always
  returned `Order.instrument = None`. Both methods now perform a reverse token lookup against
  the local SQLite instrument store and return the canonical `Instrument` (Equity, Future,
  Option, or Index). Returns `None` only for delisted instruments not present in the local
  cache.
- `InstrumentResolver.reverse_resolve(token)` — new method with in-memory caching to map
  broker tokens back to canonical instruments.
- `BrokerTransformer.token_from_order(raw)` — new protocol method; Zerodha extracts
  `instrument_token`, AngelOne extracts `symboltoken`.

## [0.7.0] - 2026-03-14

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

## [0.6.1] - 2026-03-13

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

## [0.6.0] - 2026-03-12

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

## [0.5.1] - 2026-03-12

### Changed

- Switched the project license from AGPL to Apache License 2.0.
- Added explicit `Apache-2.0` package metadata in `pyproject.toml`.
- Updated compliance guidance to clarify Apache-2.0 redistribution obligations, including
  license/attribution preservation on redistributed source or binaries, and that it does
  not require publishing source code for network or hosted use.
- Tightened trademark policy to protect `Tiny Traders`, `TT`, and `tt-connect` branding
  while keeping code reuse permissive under Apache-2.0.

## [0.5.0] - 2026-03-11

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

## [0.4.0] - 2026-03-04

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

## [0.3.0] - 2026-03-01

### Added

- Structured JSON logging via `setup_logging()` (opt-in, zero new dependencies).
- 27 named events across auth, HTTP, instrument refresh, client lifecycle, and WebSocket layers.
- `setup_logging(level="INFO", fmt="json"|"text")` exported from the top-level package.
- PR workflow templates for releases.
- MkDocs documentation recovery with GitHub Pages deploy.

## [0.2.0] - 2026-02-28

### Added

- Instrument helper APIs: `get_futures`, `get_options`, `get_expiries`, `search_instruments`.

## [0.1.0] - 2026-02-22

### Added

- Initial `tt-connect` package with unified broker abstraction for Indian markets.
- Zerodha and AngelOne adapter foundations.
- Canonical models/enums, instrument manager, and resolver.
- Unit and integration test suites with CI lint/type/test gates.
