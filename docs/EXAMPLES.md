# Complete Working Examples

Want to see everything in one file? Both examples below are fully commented, production-ready scripts that demonstrate every feature of `tt-connect`.

---

## Zerodha Example

**File:** `examples/zerodha.py` (250 lines)

**What it covers:**
- Authentication and initialization
- Profile and funds
- Instrument resolution (Index, Equity, Future, Option)
- Portfolio: holdings and positions
- Reports: order book and trade book
- Order management: place, modify, cancel, cancel-all, close-all
- Async API demo

**Run it:**
```bash
cd connect
python examples/zerodha.py
```

**Prerequisites:**
Set these environment variables or add to `.env`:
```env
ZERODHA_API_KEY=your_kite_api_key
ZERODHA_ACCESS_TOKEN=your_access_token
```

**Get credentials:**
1. Register app at https://kite.trade/
2. Complete OAuth login to get `access_token` (see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#zerodha-oauth-flow) for the step-by-step flow)

---

## AngelOne Example

**File:** `examples/angelone.py` (280 lines)

**What it covers:**
- Auto mode authentication (TOTP-based, session caching)
- Manual mode authentication (pre-obtained JWT token)
- Profile and funds
- Instrument resolution
- Portfolio: holdings and positions
- Reports: order book and trade book
- Order management
- WebSocket streaming (real-time ticks)
- Async API demo

**Run it:**
```bash
cd connect
python examples/angelone.py
```

**Prerequisites (Auto mode — recommended):**
```env
ANGELONE_API_KEY=your_smart_api_key
ANGELONE_CLIENT_ID=your_client_id
ANGELONE_PIN=1234
ANGELONE_TOTP_SECRET=JBSWY3DPEHPK3PXP
```

**Prerequisites (Manual mode):**
```env
ANGELONE_API_KEY=your_smart_api_key
ANGELONE_ACCESS_TOKEN=your_jwt_token
```

**Get credentials:**
1. Register at https://smartapi.angelbroking.com/
2. Enable TOTP in app settings and note the Base32 secret
3. For manual mode, extract `jwtToken` from login response

---

## AngelOne Instrument Store Example

**File:** `examples/angelone_store.py`

**What it covers:**
- Local `InstrumentStore` usage without placing trades
- Derivative-enabled underlyings discovery
- Instrument metadata (`lot_size`, `tick_size`, `segment`)
- Expiry lookup
- Option chain browsing
- Raw SQL escape hatch

**Run it:**
```bash
cd connect
python examples/angelone_store.py
```

**When to use it:**
- You want to explore the local instrument DB
- You need option-chain discovery without creating a trading client
- You want canonical instrument metadata for strategy tooling

**Design note:**
`InstrumentStore` is a read-only DB interface. The example refreshes the local
instrument cache through `TTConnect` first, then opens the store for queries.

---

## Both Examples Include

- ✅ Full error handling
- ✅ Context manager usage (recommended pattern)
- ✅ Manual lifecycle management alternative
- ✅ All portfolio queries (holdings, positions, funds)
- ✅ All order operations (place, modify, cancel)
- ✅ Instrument types (Index, Equity, Future, Option)
- ✅ Async API demonstration
- ✅ Real-world output formatting

---

## Why These Examples?

1. **Copy-paste ready** — Set credentials and run
2. **Fully commented** — Every section explains what's happening
3. **Production patterns** — Uses context managers, proper error handling
4. **Broker-specific notes** — Calls out differences between Zerodha and AngelOne
5. **No hidden magic** — Everything is explicit and traceable

---

## Next Steps

After running the examples:

1. **Modify for your strategy** — Replace the placeholder order logic with your own
2. **Add logging** — Use Python's `logging` module to track execution
3. **Handle errors** — Wrap order placement in try/except for production use
4. **Read the docs:**
   - [QUICKSTART.md](./QUICKSTART.md) — Step-by-step guide
   - [ARCHITECTURE.md](./ARCHITECTURE.md) — How it works internally
   - [CONTRIBUTOR_GUIDE.md](./CONTRIBUTOR_GUIDE.md) — Local development setup
