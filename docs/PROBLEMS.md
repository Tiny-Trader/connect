# tt-connect: Problems It Solves

## Core Problem

Every Indian broker is an island. Each broker exposes a completely different API surface —
different auth flows, data models, order semantics, and streaming protocols. Writing an algo
strategy means tightly coupling it to one broker. Switching brokers means a near-full rewrite.

**tt-connect** provides a single, unified interface across all Indian brokers.
Write once. Point at any broker.

---

## Problem Breakdown

### 1. Auth is a Daily Background Problem, Not a One-Time Call
- Every broker has a different auth flow
  - Zerodha (Kite): OAuth + request token exchange
  - Angel One (SmartAPI): JWT + TOTP
  - Finvasia (Shoonya): SHA256-hashed password auth
- Sessions expire daily (SEBI mandate) — re-login must be automated, not manual
- TOTP/2FA handling is inconsistent and undocumented
- Developers end up building fragile session state machines for every broker they support

### 2. No Standardized Data Model
- Same concept has 10 different names across brokers
  - LTP: `ltp` vs `last_price` vs `lastPrice` vs `close`
  - Exchange: `NSE` vs `nse_cm` vs `NSE_EQ`
- Downstream code (strategies, engines) must know broker internals

### 3. Inconsistent Symbol Naming Conventions
- Every broker uses a different format to identify the same instrument
  - Zerodha: `NSE:RELIANCE`, `NFO:NIFTY24JAN18000CE`
  - Angel One: trading symbol + exchange as separate fields
  - Finvasia: their own internal symbol format
- F&O naming is especially painful — expiry format, strike notation, and CE/PE suffix differ per broker
- Weekly vs monthly expiry symbols are formatted differently across brokers
- No universal instrument identifier exists across the Indian broker ecosystem
- Strategies hardcode broker-specific symbols, making them non-portable
- There is no validation that a symbol/expiry actually exists — bad inputs silently reach the broker and fail with cryptic errors

### 4. Inconsistent Request & Response Formats
- HTTP methods differ for the same operation — some brokers use GET for order placement, others POST
- Request body encoding varies: JSON vs form-encoded vs query params
- Response envelopes are all over the place
  - Zerodha: `{ "status": "success", "data": {...} }`
  - Angel One: `{ "status": true, "message": "...", "data": {...} }`
- Success/failure is indicated differently — HTTP status codes, boolean flags, string fields
- Pagination is implemented differently (or not at all) across brokers
- Required headers (API keys, tokens, checksums) vary per broker and per endpoint

### 5. No Order Abstraction
- Product types differ: `CNC/MIS/NRML` vs `delivery/intraday/margin`
- Order variety, validity, and disclosed quantity are named and structured differently
- Margin/leverage semantics vary per broker

### 6. Streaming is Broker-Specific
- WebSocket protocols, tick structure, and subscription methods are fully custom per broker
- No common interface for subscribing to market data or order updates

### 7. No Strategy Portability
- A strategy written for Zerodha requires significant rework to run on Angel One or any other broker
- The trading engine ends up knowing too much about the broker — wrong separation of concerns

### 8. No Sandbox / Paper Trading API
- Almost no Indian broker offers a real paper trading or sandbox API environment
- Developers are forced to test against production — slow, risky, expensive

### 9. Error Handling is Undocumented Chaos
- Broker error responses are inconsistently structured
- Rate limits differ per broker and are not always communicated in responses
- No unified way to detect, classify, or retry on errors

---

## What tt-connect Is Not

- Not a trading strategy framework
- Not a backtesting engine
- Not a data vendor or historical data provider

It is purely the **broker abstraction layer** — the plumbing between your strategy/engine and the broker.
