# tt-connect: Architecture

## Responsibilities

### 1. Universal Instrument Resolver

A SQLite-backed engine that validates canonical instrument objects against the live master and translates them to broker-specific tokens. Instrument objects are validated against the DB — not just type-checked. Requires the DB to be initialized before instrument construction.

### 2. Declarative Lifecycle Manager

Handles the auth flow, session persistence, token refresh, and TOTP automation entirely in the background. The user never calls login again after initialization. This is a state machine, not an API.

### 3. Normalization Pipeline

Bidirectional translation layer:

- **Outgoing:** canonical `Instrument` objects + enums → broker-specific request params
- **Incoming:** broker-specific JSON envelopes → canonical Pydantic models

This is what makes tt-connect an abstraction, not a wrapper. Without this, broker internals leak into user code.

### 4. Reactive Streaming Engine

Unified WebSocket wrapper — manages connection lifecycle, reconnection, and translates raw broker ticks into a stream of standardized `Tick` objects.

### 5. Duality Wrapper

Proxy layer that makes the library natively usable in both sync and async Python without maintaining two codebases. Core is async-first; sync client wraps it in one place.

---

## Project Structure

```
tt_connect/
├── __init__.py
├── client.py              # TTConnect + AsyncTTConnect
├── enums.py               # Exchange, OrderType, ProductType, Side, OptionType
├── instruments.py         # Equity, Future, Option, Currency
├── models.py              # Order, Position, Holding, Tick, Profile, Fund
├── exceptions.py          # TTConnectError, UnsupportedFeatureError, etc.
├── capabilities.py        # Capabilities dataclass + internal checker
├── instrument_manager/
│   ├── manager.py         # fetch, store, refresh lifecycle
│   ├── db.py              # SQLite interface
│   └── resolver.py        # Instrument → broker token/symbol
├── adapters/
│   ├── base.py            # BrokerAdapter base + auto-registry
│   ├── zerodha/
│   │   ├── adapter.py
│   │   ├── auth.py
│   │   ├── transformer.py # request/response normalization
│   │   └── capabilities.py
│   └── angelone/
│       ├── adapter.py
│       ├── auth.py
│       ├── transformer.py
│       └── capabilities.py
└── ws/
    ├── client.py          # WebSocket lifecycle manager
    └── normalizer.py      # raw tick → Tick model
```

**To add a new broker: create a folder under `adapters/`, implement 4 files. Touch nothing else.**

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

### 1. Instrument Manager

- Fetches, parses and stores the instrument/symbol master into SQLite
- Handles refresh lifecycle (NSE updates instruments, lot sizes, expiry calendars)
- Core job: resolves a typed instrument object to the broker-specific token/symbol
- Resolution is cached via `lru_cache` — SQLite lookups happen once per session

### 2. Broker Adapters

- One adapter per broker, each subclassing `BrokerAdapter`
- Auto-registers itself via `__init_subclass__` — no registry file to maintain
- Each adapter has 4 files: `adapter.py`, `auth.py`, `transformer.py`, `capabilities.py`
- Nothing outside the adapter knows about broker internals

### 3. REST Client

- Unified interface for: Auth, Profile, Funds, Holdings, Positions, Orders, Trades
- Sits on top of the broker adapter
- Always returns normalized Pydantic models — no broker-specific keys leak out

### 4. WebSocket Client

- Manages the streaming connection lifecycle — connect, subscribe, unsubscribe, reconnect
- Normalizes raw tick data into standard `Tick` models before emitting to the caller

### 5. Models / Schemas

- Pydantic v2 models — validation, serialization, and type safety for free
- Frozen (immutable) by default
- `Order`, `Position`, `Holding`, `Tick`, `Profile`, `Fund`

### 6. Instruments + Enums

- Typed instrument classes: `Equity`, `Future`, `Option`, `Currency`
- Enums for all categorical inputs: `Exchange`, `OptionType`, `ProductType`, `OrderType`, `Side`
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

# client.py — broker resolved from registry at runtime
class AsyncTTConnect:
    def __init__(self, broker: str, config: BrokerConfig):
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

# adapters/zerodha/capabilities.py
ZERODHA_CAPABILITIES = Capabilities(
    segments=frozenset({Exchange.NSE, Exchange.BSE, Exchange.NFO, Exchange.CDS}),
    order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.SL, OrderType.SL_M}),
    product_types=frozenset({ProductType.CNC, ProductType.MIS, ProductType.NRML}),
)
```

### Transformer Pattern

All request building and response parsing is isolated inside the broker adapter. Nothing else touches raw broker data.

```python
# adapters/zerodha/transformer.py
class ZerodhaTransformer:
    @staticmethod
    def to_order_params(instrument: Instrument, qty: int, side: Side, ...) -> dict:
        return {
            "tradingsymbol": instrument.symbol,
            "exchange": instrument.exchange.value,
            "transaction_type": "BUY" if side == Side.BUY else "SELL",
            ...
        }

    @staticmethod
    def to_order(raw: dict) -> Order:
        return Order(
            id=raw["order_id"],
            status=raw["status"],
            ...
        )
```

### Pydantic v2 Models

Validation, serialization, and IDE support for free. Frozen by default.

```python
# models.py
class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    instrument: Instrument
    side: Side
    qty: int
    status: OrderStatus
    filled_qty: int = 0
    average_price: float | None = None
```

### Sync Wrapper

Core logic is async. Sync client wraps it in one place — zero duplication.

```python
# client.py
class TTConnect:
    def __init__(self, broker: str, config: BrokerConfig):
        self._async = AsyncTTConnect(broker, config)

    def place_order(self, **kwargs) -> Order:
        return asyncio.run(self._async.place_order(**kwargs))

    def get_holdings(self) -> list[Holding]:
        return asyncio.run(self._async.get_holdings())
```

### Instrument Resolution with `lru_cache`

Symbol resolution is a SQLite lookup. Cached after first call.

```python
# instrument_manager/resolver.py
class InstrumentResolver:
    @lru_cache(maxsize=10_000)
    def resolve(self, instrument: Instrument, broker_id: str) -> str:
        # SQLite lookup → broker-specific token
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

User-configurable via `BrokerConfig`:

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

```python
# adapters/zerodha/transformer.py
ERROR_MAP: dict[str, type[TTConnectError]] = {
    "TokenException":      AuthenticationError,
    "PermissionException": AuthenticationError,
    "OrderException":      OrderError,
    "InputException":      InvalidOrderError,
    "NetworkException":    BrokerError,
}

@staticmethod
def parse_error(raw: dict) -> TTConnectError:
    code = raw.get("error_type", "")
    message = raw.get("message", "Unknown error")
    exc_class = ERROR_MAP.get(code, BrokerError)
    return exc_class(message, broker_code=code)
```

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

Create a folder under `adapters/`. Implement 4 files. Touch nothing else.

```
adapters/newbroker/
├── adapter.py       # subclass BrokerAdapter with broker_id="newbroker"
├── auth.py          # login, token refresh, session management
├── transformer.py   # to_order_params(), to_order(), to_tick(), etc.
└── capabilities.py  # NEWBROKER_CAPABILITIES = Capabilities(...)
```
