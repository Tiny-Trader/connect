# tt-connect API Layer — Implementation Plan

> **Scope** — Trading, investing, and reports APIs only.
> Historical chart data and live market quotes are out of scope for now.

> **Reality check (updated: 2026-02-22):**
> - Auth mode architecture (`manual`/`auto`) and session stores are implemented.
> - Unit + integration suites are in place and passing locally.
> - WebSocket support has started (shared interface + AngelOne WS client); treat streaming as in-progress, not out-of-scope.

---

## Status Legend

- `[ ]` Not started
- `[x]` Done

---

## Phase 0 — Auth Architecture (Option B)

> Adds a `manual` / `auto` auth mode system with optional session caching to disk.
> Foundational — must land before AngelOne or any new broker is added.

### Design

**Config shape (explicit `auth_mode` key, everything else stays the same):**

```python
# Zerodha — manual only
{
    "auth_mode":     "manual",     # optional; "manual" is default for Zerodha
    "api_key":       "...",
    "access_token":  "...",        # required on first run (or if no cached session)
    "cache_session": True,         # default False; writes _cache/zerodha_session.json
}

# AngelOne — auto (default) — full TOTP login, no human needed
{
    "auth_mode":     "auto",       # optional; "auto" is default for AngelOne
    "api_key":       "...",
    "client_id":     "...",
    "pin":           "...",
    "totp_secret":   "...",
    "cache_session": True,         # strongly recommended; avoids re-login on every init
}

# AngelOne — manual (user pre-obtains jwt_token themselves)
{
    "auth_mode":     "manual",
    "api_key":       "...",
    "access_token":  "...",        # jwt_token from manual login
    "cache_session": False,
}
```

**Session file** (written to `_cache/{broker_id}_session.json` when `cache_session=True`):

```json
{
  "broker":        "angelone",
  "mode":          "auto",
  "access_token":  "eyJ...",
  "refresh_token": "...",
  "feed_token":    "...",
  "obtained_at":   "2026-02-21T09:00:00+05:30",
  "expires_at":    "2026-02-22T00:00:00+05:30"
}
```

**Token expiry by broker:**
- Zerodha — 6:00 AM IST next day (hard limit, no refresh API exists)
- AngelOne — midnight IST; has a `renewToken` endpoint for refresh without re-login

**On 401 / expired token:**
- `auto` mode → call `refresh()` → if that fails, full re-login → update cache
- `manual` mode → raise `AuthenticationError` with a clear message telling the user to re-run `get_token.py` or pass a fresh `access_token`

---

### New files

- [x] **`tt_connect/auth/__init__.py`**
- [x] **`tt_connect/auth/base.py`** — `AuthMode` enum, `SessionData` dataclass, `BaseAuth` abstract class
  - `AuthMode`: `MANUAL = "manual"`, `AUTO = "auto"`
  - `SessionData`: `access_token`, `refresh_token | None`, `feed_token | None`, `obtained_at`, `expires_at | None`, `is_expired() -> bool`
  - `BaseAuth`: holds `_session: SessionData | None`, `_store`, `_mode`; implements `login()` dispatch, `save/load` helpers; abstract `_login_manual()`, `_login_auto()`, `_refresh_auto()`, `headers` property, `_default_mode`, `_supported_modes`
- [x] **`tt_connect/auth/store.py`** — session persistence
  - `BaseSessionStore` — `load(broker_id) -> SessionData | None`, `save(broker_id, session)`, `clear(broker_id)`
  - `MemorySessionStore` — in-process only, lost on restart
  - `FileSessionStore` — reads/writes `_cache/{broker_id}_session.json`; created automatically when `cache_session=True` in config

### Modified files

- [x] **`tt_connect/enums.py`** — add `AuthMode` enum (`MANUAL`, `AUTO`)
- [x] **`tt_connect/capabilities.py`** — add `auth_modes: frozenset[AuthMode]` field + `verify_auth_mode()` method
- [x] **`tt_connect/adapters/zerodha/capabilities.py`** — `auth_modes=frozenset({AuthMode.MANUAL})`
- [x] **`tt_connect/adapters/angelone/capabilities.py`** — `auth_modes=frozenset({AuthMode.MANUAL, AuthMode.AUTO})`
- [x] **`tt_connect/adapters/zerodha/auth.py`** — refactor `ZerodhaAuth` to extend `BaseAuth`
  - `_default_mode = AuthMode.MANUAL`
  - calls `capabilities.verify_auth_mode(mode)` on init — raises `UnsupportedFeatureError` if `auth_mode=auto`
  - `_login_manual()` — read `access_token` from config; set `expires_at` = next 6 AM IST
  - `_login_auto()` — raises `UnsupportedFeatureError("Zerodha does not support automated login")`
  - `_refresh_auto()` — raises `UnsupportedFeatureError`
  - `headers` — unchanged (`token {api_key}:{access_token}` + `X-Kite-Version: 3`)
- [x] **`tt_connect/adapters/angelone/auth.py`** — refactor `AngelOneAuth` to extend `BaseAuth`
  - `_default_mode = AuthMode.AUTO`
  - `_supported_modes = {AuthMode.MANUAL, AuthMode.AUTO}`
  - `_login_auto()` — POST `/loginByPassword` with `client_id + pin + totp`; stores `jwtToken`, `refreshToken`, `feedToken`; sets `expires_at` = midnight IST
  - `_login_manual()` — read `access_token` from config; set `expires_at` = midnight IST
  - `_refresh_auto()` — POST `/renewToken` with `refreshToken`; update all three tokens; fall back to full `_login_auto()` on failure
  - `headers` — `Authorization: Bearer {jwt_token}` + AngelOne's 7 other required headers
- [ ] **`tt_connect/adapters/base.py`** — add `auth` abstract property typed to `BaseAuth`

### Backwards compatibility

- Zerodha configs with no `auth_mode` key — defaults to `"manual"`, same as today ✅
- AngelOne configs with no `auth_mode` key — defaults to `"auto"`, same as today ✅
- No change to any public client API (`TTConnect`, `AsyncTTConnect`) ✅

---

## What's Already Done

- [x] DB schema — instruments, equities, futures, options, broker_tokens, \_meta
- [x] Instrument types — Index, Equity, Future, Option (Pydantic)
- [x] InstrumentManager — full parse + insert pipeline (indices, equities, futures, options)
- [x] InstrumentResolver — Index, Equity, Future, Option (live-tested)
- [x] Zerodha auth — Option A (token injection), get_token.py dev helper
- [x] Zerodha adapter — all REST endpoint stubs wired (login, fetch_instruments, profile, funds, holdings, positions, orders CRUD)
- [x] Zerodha transformer — to_profile, to_fund (basic), to_order, to_order_params, parse_error
- [x] AsyncTTConnect / TTConnect — init, close, resolve, place_order, modify_order, cancel_order, get_order, get_orders, get_holdings, get_positions
- [x] Live tested — auth, indices, equities, index F&O, equity F&O (NIFTY, BANKNIFTY, MIDCPNIFTY, SBIN, ITC)

---

## Phase 1 — Enrich Models

> Models need to carry all fields that Zerodha returns so transformers can populate them properly.

- [x] **`Fund` model** — add `collateral`, `m2m_unrealized`, `m2m_realized`, `utilised_debits`
  - Zerodha returns: `equity.available.collateral`, `equity.utilised.m2m_unrealised`, `equity.utilised.m2m_realised`, `equity.utilised.debits`
- [x] **`Holding` model** — add `pnl_percent`
  - Computed as `(ltp - avg_price) / avg_price * 100`
- [x] **`Trade` model** — new model for trade book entries
  - Fields: `order_id`, `instrument`, `side`, `qty`, `avg_price`, `trade_value`, `product`, `timestamp`
- [x] **`Margin` model** — new model for margin calculation results
  - Fields: `total`, `span`, `exposure`, `option_premium`, `final_total`, `benefit`
  - `benefit = initial.total - final.total` (spread credit)

---

## Phase 2 — Complete Zerodha Transformer

> These are called today from the client but raise `AttributeError` since they don't exist yet.

- [x] **`to_holding(raw)`**
  - Maps: `tradingsymbol → instrument.symbol`, `exchange`, `quantity`, `average_price`, `last_price → ltp`, `pnl`, compute `pnl_percent`
  - Note: holdings do not carry an `Instrument` object — resolve from `tradingsymbol + exchange`
- [x] **`to_position(raw)`**
  - Maps from `data.net[]`: `tradingsymbol`, `exchange`, `quantity` (net), `average_price`, `last_price → ltp`, `pnl`, `product`
  - Skip rows where `quantity == 0` (flat positions)
- [x] **`to_trade(raw)`**
  - Maps from `/trades`: `order_id`, `tradingsymbol → instrument`, `transaction_type → side`, `quantity`, `average_price`, `quantity * average_price → trade_value`, `product`, `fill_timestamp`
- [x] **`to_fund(raw)`** — extend existing implementation
  - Add: `collateral`, `m2m_unrealized`, `m2m_realized`, `utilised_debits`
- [x] **`to_margin(raw)`** — new
  - Maps `/margins/basket` response to `Margin` model

---

## Phase 3 — Zerodha Adapter

> HTTP wiring for the remaining endpoints.

- [x] **`get_trades()`** — `GET /trades`
- [ ] **`calculate_margin(orders)`** — `POST /margins/basket?consider_positions=true`
  - Request body: list of order dicts in Zerodha format (exchange, tradingsymbol, transaction_type, variety, product, order_type, quantity, price, trigger_price)
  - Also add `to_margin_params()` to transformer for the outgoing transform
- [x] **Base adapter** — add abstract stub for `get_trades()`

---

## Phase 4 — AsyncTTConnect Client

> Expose the above to end users through the public API.

- [x] **`get_trades() -> list[Trade]`**
- [ ] **`calculate_margin(instruments) -> Margin`**
  - Accepts a list of `(Instrument, qty, side, product, order_type)` tuples
  - Resolves each instrument to a broker token + builds Zerodha margin payload
- [x] **`cancel_all_orders() -> tuple[list[str], list[str]]`** — client-side logic
  - Fetch orders → filter status `OPEN` or `TRIGGER PENDING` → cancel each → return (cancelled_ids, failed_ids)
- [x] **`close_all_positions()`** — client-side logic
  - Fetch positions → for each non-zero position, place offsetting market order
  - Long (qty > 0) → SELL MIS/NRML; Short (qty < 0) → BUY

---

## Phase 5 — Dev Tests (Zerodha)

> All tests use the public `AsyncTTConnect` API, not internal methods.
> Order-writing tests (cancel_all, close_all) are safe because we have no open positions.

- [x] **`test_live_portfolio.py`** — holdings, positions, orders, trades, funds (live-tested)
- [ ] **`test_live_margin.py`** — `calculate_margin()` with NIFTY FUT + a CE/PE pair

---

## Phase 6 — Hardening

- [x] **Unit tests** — parser, transformer (to_holding, to_position, to_trade, to_fund, to_order) using fixture dicts, no real API calls
- [ ] **`on_stale=WARN`** path tested — verify stale DB serves cached data instead of crashing
- [ ] **Retry / timeout** — add `httpx.Timeout` and retry on transient 5xx to `_request()` in base adapter
- [ ] **Graceful `init()` failure** — if instrument download fails on first run (no cached DB), surface a clear error

---

## Out of Scope (for now)

- Historical OHLC data
- Live market quotes (REST polling)
- MCX / CDS instruments
- Basket orders / GTT orders
- Options strategy margin (multi-leg)
