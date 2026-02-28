# tt-connect: Architecture

## Responsibilities

### 1. Universal Instrument Resolver

A SQLite-backed engine that validates canonical instrument objects against the live master and translates them to broker-specific tokens. Instrument objects are validated against the DB — not just type-checked. Requires the DB to be initialized before instrument construction.

### 2. Declarative Lifecycle Manager

Handles the auth flow, session persistence, token refresh, and TOTP automation entirely in the background. The user never calls login again after initialization. This is a state machine, not an API.

### 3. Normalization Pipeline

Bidirectional translation layer:

- **Outgoing:** canonical `PlaceOrderRequest` / `ModifyOrderRequest` objects + enums → broker-specific request params
- **Incoming:** broker-specific JSON envelopes → canonical Pydantic models

This is what makes tt-connect an abstraction, not a wrapper. Without this, broker internals leak into user code.

### 4. Reactive Streaming Engine

Unified WebSocket wrapper — manages connection lifecycle, reconnection, and translates raw broker ticks into a stream of standardized `Tick` objects.

### 5. Duality Wrapper

Proxy layer that makes the library natively usable in both sync and async Python without maintaining two codebases. Core is async-first; sync client wraps it in a single dedicated thread.

---

## Project Structure

```text
tt_connect/
├── __init__.py           # Public exports: TTConnect, AsyncTTConnect, PlaceOrderRequest, ModifyOrderRequest, PlaceGttRequest, ModifyGttRequest, Gtt, GttLeg
├── client.py             # AsyncTTConnect (public facade) + _AsyncTTConnectCore (internal)
├── lifecycle.py          # _ClientBase + LifecycleMixin (init, close, state, WebSocket)
├── portfolio.py          # PortfolioMixin (get_profile, get_funds, holdings, positions, trades)
├── orders.py             # OrdersMixin (place, modify, cancel, get orders, close positions)
├── instruments_mixin.py  # InstrumentsMixin (get_futures, get_options, get_expiries, search)
├── sync_client.py        # TTConnect — threaded sync wrapper over AsyncTTConnect
├── enums.py              # Exchange, OrderType, ProductType, Side, OptionType, ClientState
├── instruments.py        # Equity, Future, Option, Currency
├── models.py             # Response models + PlaceOrderRequest, ModifyOrderRequest
├── exceptions.py         # TTConnectError hierarchy + lifecycle errors
├── capabilities.py       # Capabilities dataclass + internal checker
├── instrument_manager/
│   ├── manager.py        # fetch, store, refresh lifecycle
│   ├── db.py             # SQLite interface
│   └── resolver.py       # Instrument → broker token/symbol
├── adapters/
│   ├── base.py           # BrokerAdapter base + auto-registry + BrokerTransformer Protocol
│   ├── zerodha/
│   │   ├── adapter.py
│   │   ├── auth.py
│   │   ├── transformer.py  # request/response normalization
│   │   ├── parser.py       # instrument master CSV parsing
│   │   └── capabilities.py
│   └── angelone/
│       ├── adapter.py
│       ├── auth.py
│       ├── transformer.py
│       ├── parser.py       # instrument master JSON parsing
│       └── capabilities.py
└── ws/
    ├── client.py           # BrokerWebSocket abstract + OnTick type
    ├── angelone.py         # AngelOne WebSocket (SmartAPI stream)
    └── zerodha.py          # Zerodha WebSocket (KiteTicker binary protocol)
```

**To add a new broker: create a folder under `adapters/`, implement 5 files. Touch nothing else.**

---

## Technology Decisions

| Concern             | Choice      | Reason                                                                                    |
| ------------------- | ----------- | ----------------------------------------------------------------------------------------- |
| Models / Validation | Pydantic v2 | Runtime type enforcement critical for trading; built in Rust, fast; ubiquitous dependency |
| SQLite access       | `aiosqlite` | Thin async wrapper over stdlib `sqlite3`, minimal overhead, no ORM magic                  |
| HTTP client         | `httpx`     | Native async support, sync client available, clean API                                    |
| Core design         | Async-first | Trading engines are event-driven; sync client wraps async in one place                    |

---

## Components

### 1. Client Lifecycle (State Machine)

`AsyncTTConnect` and `TTConnect` track an explicit `ClientState`:

```text
CREATED  →  (await init())  →  CONNECTED  →  (await close())  →  CLOSED
```

All data methods call `_require_connected()` internally. Calling an operation on a `CREATED` or `CLOSED` client raises a typed, catchable error instead of a cryptic `AssertionError`:

```python
ClientNotConnectedError  # init() has not been called
ClientClosedError        # close() has already been called — client cannot be reused
InstrumentManagerError   # internal: instrument DB used before init()
```

Both clients support context managers as the recommended lifecycle pattern:

```python
# Async
async with AsyncTTConnect("zerodha", config) as broker:
    profile = await broker.get_profile()

# Sync
with TTConnect("zerodha", config) as broker:
    profile = broker.get_profile()
```

### 2. Mixin Decomposition

`AsyncTTConnect` is a clean public facade that delegates to an internal `_AsyncTTConnectCore`, which is assembled from four mixins each in its own file:

```python
class _AsyncTTConnectCore(LifecycleMixin, PortfolioMixin, OrdersMixin, InstrumentsMixin):
    """Internal implementation class. Use AsyncTTConnect publicly."""
```

All four inherit from `_ClientBase` (defined in `lifecycle.py`), which declares the shared attributes (`_adapter`, `_resolver`, `_state`, etc.) so mypy can type-check each mixin independently. The facade pattern keeps internal state and methods (`_require_connected`, `_resolve`, etc.) off the public API surface.

### 3. Instrument Manager

- Fetches, parses and stores the instrument/symbol master into SQLite
- Handles refresh lifecycle (NSE updates instruments, lot sizes, expiry calendars)
- Core job: resolves a typed instrument object to the broker-specific token/symbol
- Resolution is cached via `lru_cache` — SQLite lookups happen once per session

### 4. Broker Adapters

- One adapter per broker, each subclassing `BrokerAdapter`
- Auto-registers itself via `__init_subclass__` — no registry file to maintain
- Each adapter has 5 files: `adapter.py`, `auth.py`, `transformer.py`, `parser.py`, `capabilities.py`
- Nothing outside the adapter knows about broker internals

### 5. REST Client

- Unified interface for: Auth, Profile, Funds, Holdings, Positions, Orders, Trades
- Sits on top of the broker adapter
- Always returns normalized Pydantic models — no broker-specific keys leak out

### 6. WebSocket Client

- Manages the streaming connection lifecycle — connect, subscribe, unsubscribe, reconnect
- Normalizes raw tick data into standard `Tick` models before emitting to the caller
- Always subscribes in the richest available mode: `full` for Zerodha (OI, bid/ask, timestamps, market depth) and `SNAP_QUOTE` (mode 3) for AngelOne (OI, best-5 bid/ask). Binary parsers already handle all fields — no user configuration needed.

### 7. Models / Schemas

- **Response models** (frozen Pydantic): `Order`, `Position`, `Holding`, `Tick`, `Profile`, `Fund`, `Gtt`
- **Request models** (mutable Pydantic): `PlaceOrderRequest`, `ModifyOrderRequest`, `PlaceGttRequest`, `ModifyGttRequest`

Request models are validated at construction — bad fields surface before any network call.

### 8. Instruments + Enums

- Typed instrument classes: `Equity`, `Future`, `Option`, `Currency`
- Enums for all categorical inputs: `Exchange`, `OptionType`, `ProductType`, `OrderType`, `Side`, `ClientState`
- Symbols follow NSE official naming conventions as the canonical standard
- Validation at object construction — bad inputs fail before any network call

---

## Key Patterns

### Auto-registration via `__init_subclass__`

No registry file to maintain. A broker registers itself just by existing.

```python
# adapters/base.py
class BrokerAdapter:
    _registry: ClassVar[dict[str, type[BrokerAdapter]]] = {}

    def __init_subclass__(cls, broker_id: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if broker_id:
            BrokerAdapter._registry[broker_id] = cls

# adapters/zerodha/adapter.py
class ZerodhaAdapter(BrokerAdapter, broker_id="zerodha"):
    ...

# lifecycle.py — broker resolved from registry at runtime
class LifecycleMixin:
    def __init__(self, broker: str, config: dict):
        self._adapter = BrokerAdapter._registry[broker](config)
```

### Capability Checking

Capability matrix is internal to each adapter. Check happens before any network call. No capability API is exposed to the user.

```python
# capabilities.py
@dataclass(frozen=True)
class Capabilities:
    segments: frozenset[Exchange]
    order_types: frozenset[OrderType]
    product_types: frozenset[ProductType]

    def verify(self, instrument: Instrument, order_type: OrderType, product_type: ProductType):
        if instrument.exchange not in self.segments:
            raise UnsupportedFeatureError(f"{instrument.exchange} segment not supported")
        if order_type not in self.order_types:
            raise UnsupportedFeatureError(f"{order_type} not supported")
```

### Transformer Pattern

All request building and response parsing is isolated inside the broker adapter. Nothing else touches raw broker data.

```python
# adapters/zerodha/transformer.py
class ZerodhaTransformer:

    @staticmethod
    def to_order_params(
        token: str, broker_symbol: str, exchange: str, req: PlaceOrderRequest
    ) -> dict:
        return {
            "tradingsymbol":    broker_symbol,
            "exchange":         exchange,
            "transaction_type": req.side.value,
            "quantity":         req.qty,
            "product":          req.product.value,
            "order_type":       req.order_type.value,
            "validity":         "DAY",
        }

    @staticmethod
    def to_modify_params(req: ModifyOrderRequest) -> dict:
        params = {}
        if req.qty is not None:   params["quantity"]      = req.qty
        if req.price is not None: params["price"]         = req.price
        if req.order_type:        params["order_type"]    = req.order_type.value
        return params

    @staticmethod
    def to_order(raw: dict) -> Order:
        return Order(
            id=raw["order_id"],
            status=_ORDER_STATUS_MAP.get(raw["status"], OrderStatus.PENDING),
            ...
        )
```

### Pydantic v2 Models

Validation, serialization, and IDE support for free. Response models are frozen; request models are mutable.

```python
# models.py
class Order(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    instrument: Instrument | None
    side: Side
    qty: int
    status: OrderStatus
    filled_qty: int
    avg_price: float | None = None

class PlaceOrderRequest(BaseModel):
    instrument: Instrument
    side: Side
    qty: int
    order_type: OrderType
    product: ProductType
    price: float | None = None
    trigger_price: float | None = None
```

### Sync Wrapper

Core logic is async. `TTConnect` wraps it with a dedicated background thread running an event loop — zero code duplication.

```python
# sync_client.py
class TTConnect:
    def __init__(self, broker: str, config: dict):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncTTConnect(broker, config)
        self._run(self._async.init())

    def _run(self, coro) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def place_order(self, req: PlaceOrderRequest) -> str:
        return self._run(self._async.place_order(req))
```

### Instrument Resolution with `lru_cache`

Symbol resolution is a SQLite lookup. Cached after first call.

```python
# instrument_manager/resolver.py
class InstrumentResolver:
    @lru_cache(maxsize=10_000)
    def resolve(self, instrument: Instrument, broker_id: str) -> ResolvedInstrument:
        # SQLite lookup → broker-specific token, symbol, exchange
        ...
```

---

## Instrument Manager

### Cache Directory

All runtime artifacts live in `_cache/` at the project root:

```
_cache/
├── {broker_id}_instruments.db   # SQLite instrument master (isolated per broker)
├── {broker_id}_session.json     # broker session tokens (for auto login mode)
```

### Stale Data Behaviour

User-configurable via config:

- `on_stale="fail"` — hard fail if instrument dump cannot be refreshed at startup (default)
- `on_stale="warn"` — log a warning and continue with stale data

### Schema

Normalized structure — separates instrument identity from broker-specific tokens.
Instrument type specific fields live in their own tables. No NULL columns.

```sql
-- Canonical instrument identity
CREATE TABLE instruments (
    id        INTEGER PRIMARY KEY,
    exchange  TEXT NOT NULL,
    symbol    TEXT NOT NULL,
    name      TEXT,
    lot_size  INTEGER,
    tick_size REAL
);

CREATE TABLE equities (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    isin          TEXT
);

CREATE TABLE futures (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_id INTEGER NOT NULL REFERENCES instruments(id),
    expiry        DATE NOT NULL
);

CREATE TABLE options (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_id INTEGER NOT NULL REFERENCES instruments(id),
    expiry        DATE NOT NULL,
    strike        REAL NOT NULL,
    option_type   TEXT NOT NULL  -- CE, PE
);

-- One canonical instrument maps to N broker tokens
CREATE TABLE broker_tokens (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    broker_id     TEXT NOT NULL,
    token         TEXT NOT NULL,
    PRIMARY KEY (instrument_id, broker_id)
);

-- Indices for fast resolution
CREATE INDEX idx_instruments ON instruments(exchange, symbol);
CREATE INDEX idx_futures      ON futures(underlying_id, expiry);
CREATE INDEX idx_options      ON options(underlying_id, expiry, strike, option_type);
```

**Insert order during refresh:** `instruments` → type table (`equities`/`futures`/`options`) → `broker_tokens`.
Underlyings (e.g. NIFTY equity) must be inserted before futures/options that reference them.

### Refresh Lifecycle

Rebuild from scratch daily — truncate all tables and re-fetch from broker on startup if `last_updated` is not today.
No delta updates, no diffing.

---

## Error Handling

### Exception Hierarchy (`exceptions.py`)

Canonical exception types shared across the entire library. User only ever catches these.

```python
class TTConnectError(Exception): ...

# Lifecycle
class ClientNotConnectedError(TTConnectError): ...  # init() not called
class ClientClosedError(TTConnectError): ...        # client already closed
class InstrumentManagerError(TTConnectError): ...   # internal: DB used before init()

# Broker / Network
class AuthenticationError(TTConnectError):     retryable = False
class RateLimitError(TTConnectError):          retryable = True
class InsufficientFundsError(TTConnectError):  retryable = False
class InstrumentNotFoundError(TTConnectError): retryable = False
class UnsupportedFeatureError(TTConnectError): retryable = False
class OrderError(TTConnectError):              retryable = False
class InvalidOrderError(OrderError):           retryable = False
class OrderNotFoundError(OrderError):          retryable = False
class BrokerError(TTConnectError):             retryable = False  # catch-all for unmapped errors
```

### Error Map (per broker transformer)

Each broker transformer declares a map from its own error codes to canonical exceptions.
Unmapped errors fall back to `BrokerError`, preserving the raw code and message.

### Central Error Check in Adapter Base

Every HTTP response passes through one method. Error detection and raising happens once.

```python
# adapters/base.py
async def _request(self, method, url, **kwargs) -> dict:
    response = await self._client.request(method, url, **kwargs)
    raw = response.json()
    if self._is_error(raw, response.status_code):
        raise self.transformer.parse_error(raw)
    return raw
```

Each broker overrides `_is_error()` since success/failure is indicated differently per broker.

---

## Broker Capability Handling

Each broker adapter has an internal capability matrix declaring what it supports — segments, order types, product types etc.

**The library does not expose capabilities to the user.** If an unsupported operation is attempted, the library raises immediately with a clear error before any network call is made.

```
UnsupportedFeatureError: Zerodha does not support MCX segment
UnsupportedFeatureError: AngelOne does not support this order type
```

No warnings. No fallbacks. No user-side capability checks.

---

## Adding a New Broker

Create a folder under `adapters/`. Implement 5 files. Touch nothing else.

```
adapters/newbroker/
├── adapter.py       # subclass BrokerAdapter with broker_id="newbroker"
├── auth.py          # login, token refresh, session management
├── transformer.py   # to_order_params(), to_modify_params(), to_order(), to_tick(), etc.
├── parser.py        # instrument master file parsing (CSV, JSON, etc.)
└── capabilities.py  # NEWBROKER_CAPABILITIES = Capabilities(...)
```
