# Core ↔ Broker Integration

How the `core/` and `brokers/` packages connect at each stage of the application lifecycle.

## Dependency Rule

**Arrows only flow from `brokers/ → core/`** (imports). Core never does `from tt_connect.brokers.zerodha import ...`. The connection is always through registries, Protocols, or base classes.

---

## 1. Auto-Registration (Import Time)

When Python imports `tt_connect`, the `brokers/__init__.py` auto-discovers all broker packages. Each broker's `__init__.py` imports its adapter and config, which triggers `__init_subclass__`:

```
App does: from tt_connect import TTConnect
  │
  ├── tt_connect/__init__.py imports brokers
  │     └── brokers/__init__.py scans subpackages via pkgutil
  │           ├── import brokers.zerodha
  │           │     ├── import zerodha.adapter  →  class ZerodhaAdapter(BrokerAdapter, broker_id="zerodha")
  │           │     │                                  └── __init_subclass__ writes to BrokerAdapter._registry["zerodha"]
  │           │     └── import zerodha.config   →  class ZerodhaConfig(BrokerConfig, broker_id="zerodha")
  │           │                                        └── __init_subclass__ writes to BrokerConfig._registry["zerodha"]
  │           └── import brokers.angelone (same pattern)
  │
  ▼
  BrokerAdapter._registry = {"zerodha": ZerodhaAdapter, "angelone": AngelOneAdapter}
  BrokerConfig._registry  = {"zerodha": ZerodhaConfig,  "angelone": AngelOneConfig}
```

**Core defines the registries. Brokers populate them. Core reads them by string key.**

---

## 2. The `init()` Flow (Runtime)

When the user calls `await client.init()`, here's how core and broker code interact:

```
User: client = TTConnect("zerodha", {"api_key": "...", "access_token": "..."})
      await client.init()

  LifecycleMixin.__init__("zerodha", config)
  │
  ├── BrokerAdapter._registry["zerodha"]  →  ZerodhaAdapter class
  │     └── ZerodhaAdapter(config)
  │           ├── validate_config("zerodha", config)
  │           │     └── BrokerConfig._registry["zerodha"]  →  ZerodhaConfig
  │           │           └── ZerodhaConfig.model_validate(config)  ← Pydantic validation
  │           ├── self.auth = ZerodhaAuth(config, http_client)
  │           └── self._transformer = ZerodhaTransformer()
  │
  ├── await client.init()
  │     ├── await adapter.login()           ← core calls broker auth
  │     ├── await instrument_manager.init(adapter.fetch_instruments)
  │     │     └── await adapter.fetch_instruments()   ← core calls broker parser
  │     │           ├── HTTP GET /instruments
  │     │           └── parse(csv)  →  ParsedInstruments (satisfies ParsedInstrumentsLike Protocol)
  │     │                 └── manager._insert(parsed)  ← core reads .indices, .equities, etc.
  │     └── resolver = InstrumentResolver(db_conn, "zerodha")
  │
  ▼
  Client is CONNECTED — ready for orders/quotes/streaming
```

---

## 3. The Order Flow

```
User: await client.place_order(PlaceOrderRequest(instrument=nifty_fut, ...))

  OrdersMixin.place_order(req)
  │
  ├── resolver.resolve(req.instrument)                    ← CORE (SQLite lookup)
  │     └── ResolvedInstrument(token="12345", broker_symbol="NIFTY26MARFUT", exchange="NFO")
  │
  ├── adapter.capabilities.verify(instrument, ...)        ← CORE calls BROKER's Capabilities
  │     └── "Is NFO supported? Is LIMIT supported?"       (fail fast before network call)
  │
  ├── adapter.transformer.to_order_params(token, symbol, exchange, req)   ← BROKER transforms
  │     └── {"tradingsymbol": "NIFTY26MARFUT", "exchange": "NFO", "transaction_type": "BUY", ...}
  │
  ├── adapter.place_order(params)                         ← BROKER makes HTTP call
  │     └── POST https://api.kite.trade/orders/regular
  │           └── returns raw JSON {"status": "success", "data": {"order_id": "ABC123"}}
  │
  ├── adapter.transformer.to_order_id(raw)                ← BROKER extracts order ID
  │     └── "ABC123"
  │
  ▼
  Returns "ABC123" to user
```

---

## 4. The Streaming Flow

```
User: await client.subscribe([nifty_index], on_tick=my_callback)

  LifecycleMixin.subscribe(instruments, on_tick)
  │
  ├── resolver.resolve(nifty_index)                       ← CORE (SQLite lookup)
  │     └── ResolvedInstrument(token="256265", ...)
  │
  ├── adapter.create_ws_client()                          ← BROKER creates WS instance
  │     └── ZerodhaWebSocket(api_key, access_token)
  │
  ├── ws.subscribe([(instrument, resolved)], on_tick)     ← BROKER opens connection
  │     └── wss://ws.kite.trade?api_key=xxx&access_token=yyy
  │           └── sends {"a": "subscribe", "v": [256265]}
  │           └── sends {"a": "mode", "v": ["full", [256265]]}
  │
  │   On each binary message:
  │     ├── ws._parse_binary_message(data)                ← BROKER parses binary
  │     │     └── Tick(instrument=nifty_index, ltp=23450.0, volume=..., oi=..., bid=..., ask=...)
  │     └── await on_tick(tick)                           ← user's callback
  │
  ▼
  Ticks flow continuously until unsubscribe/close
```

---

## Connection Seams

| Seam             | Core side                        | Broker side                     | Connection mechanism            |
| ---------------- | -------------------------------- | ------------------------------- | ------------------------------- |
| **Adapter**      | `BrokerAdapter` base class       | `ZerodhaAdapter` subclass       | `__init_subclass__` registry    |
| **Config**       | `BrokerConfig` base class        | `ZerodhaConfig` subclass        | `__init_subclass__` registry    |
| **Transformer**  | `BrokerTransformer` Protocol     | `ZerodhaTransformer` class      | Structural typing (duck typing) |
| **Auth**         | `BaseAuth` base class            | `ZerodhaAuth` subclass          | Classical inheritance           |
| **WebSocket**    | `BrokerWebSocket` ABC            | `ZerodhaWebSocket` subclass     | Classical inheritance           |
| **Parser**       | `ParsedInstrumentsLike` Protocol | `ParsedInstruments` dataclass   | Structural typing               |
| **Capabilities** | `Capabilities` dataclass         | `ZERODHA_CAPABILITIES` instance | Plain data                      |

---

## File-Level Dependency Graph

```
              ┌─────────────────────────────────────────────┐
              │              brokers/zerodha/                │
              │  config.py ──→ core/models/config.py        │
              │  auth.py ────→ core/adapter/auth.py         │
              │  adapter.py ─→ core/adapter/base.py         │
              │  transformer → core/models/* + exceptions   │
              │  parser.py ──→ core/models/enums.py         │
              │  ws.py ──────→ core/adapter/ws.py           │
              │  capabilities → core/adapter/capabilities   │
              └──────────────────────┬──────────────────────┘
                                     │ imports
                                     ▼
              ┌─────────────────────────────────────────────┐
              │                   core/                     │
              │  client/   ── uses ──→  adapter/ + store/   │
              │  adapter/  ── uses ──→  models/ + exceptions│
              │  store/    ── uses ──→  models/ + exceptions│
              │  models/   ── uses ──→  enums (leaf)        │
              │  exceptions.py         (leaf — no deps)     │
              └─────────────────────────────────────────────┘
```

Every arrow points inward/downward. No circular dependencies. No core → broker imports.
