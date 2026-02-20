# tt-connect API Layer — Implementation Plan

> **Scope** — Trading, investing, and reports APIs only.
> Historical chart data, live market quotes, and WebSockets are explicitly out of scope for now.

---

## Status Legend

- `[ ]` Not started
- `[x]` Done

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

- [ ] **Unit tests** — parser, transformer (to_holding, to_position, to_trade, to_fund, to_order) using fixture dicts, no real API calls
- [ ] **`on_stale=WARN`** path tested — verify stale DB serves cached data instead of crashing
- [ ] **Retry / timeout** — add `httpx.Timeout` and retry on transient 5xx to `_request()` in base adapter
- [ ] **Graceful `init()` failure** — if instrument download fails on first run (no cached DB), surface a clear error

---

## Out of Scope (for now)

- Historical OHLC data
- Live market quotes (REST polling)
- WebSocket tick streaming
- MCX / CDS instruments
- Basket orders / GTT orders
- Options strategy margin (multi-leg)
