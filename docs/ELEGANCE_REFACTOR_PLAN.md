# Elegance Refactor Plan (Code-First)

This document records a code-centric assessment of current design quality and
defines a concrete path to make the package genuinely elegant.

Scope:
- Focuses on implementation, not documentation quality.
- Uses "elegant" to mean: inevitable API shape, explicit lifecycle, strong
  boundaries, minimal surprises, and low cognitive load.

## Elegance Standard Used

For this project, software is considered elegant when:

1. The API is unsurprising and explicit.
2. Each component has one clear responsibility.
3. Public interfaces never leak broker-specific implementation details.
4. Lifecycle and state are explicit, deterministic, and easy to reason about.
5. Error behavior is typed and predictable.
6. Extension is additive (new broker module), not cross-cutting edits.

## Current Assessment

The codebase has a strong architectural spine, but is not fully elegant yet.

What is already strong:

- Adapter boundary is real and mostly respected.
- Canonical models and enums are centralized.
- Instrument manager + resolver separation is clear.
- Async-first core with sync access is directionally correct.

What currently breaks elegance:

1. Hidden lifecycle work in constructors.
2. Leaky abstraction in order modification APIs.
3. Partial canonical outputs (`Order.instrument` can be `None`).
4. Broad `except Exception` paths in bulk operations.
5. Import side effects for adapter registration.
6. Loose typing (`Any`) at core interface boundaries.

## Current vs Proposed (Code-Level)

### 1) Lifecycle: Constructor Side Effects vs Explicit Connection

Current:

```python
class TTConnect:
    def __init__(self, broker: str, config: dict[str, Any]):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncTTConnect(broker, config)
        self._run(self._async.init())  # network/auth/db init here
```

Proposed:

```python
class AsyncTTConnect:
    async def connect(self) -> None: ...
    async def close(self) -> None: ...

    async def __aenter__(self) -> "AsyncTTConnect":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

class TTConnect:
    def connect(self) -> None: ...
    def close(self) -> None: ...

    def __enter__(self) -> "TTConnect":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
```

Why this is more elegant:
- No hidden I/O in `__init__`.
- Resource ownership becomes explicit and deterministic.
- Fewer surprises in tests and production bootstrapping.

### 2) Public API: Canonical Requests vs Broker-Native kwargs

Current:

```python
async def modify_order(self, order_id: str, **kwargs: Any) -> None:
    await self._adapter.modify_order(order_id, kwargs)
```

Proposed:

```python
class ModifyOrderRequest(BaseModel):
    order_id: str
    qty: int | None = None
    price: float | None = None
    trigger_price: float | None = None

async def modify_order(self, req: ModifyOrderRequest) -> str:
    params = self._adapter.transformer.to_modify_params(req)
    raw = await self._adapter.modify_order(req.order_id, params)
    return self._adapter.transformer.to_order_id(raw)
```

Why this is more elegant:
- Single canonical shape across brokers.
- Better validation before network calls.
- Better IDE discoverability and safer refactors.

### 3) Domain Model Invariant: Optional Instrument vs Guaranteed Instrument

Current:

```python
class Order(BaseModel):
    instrument: Instrument | None = None
```

Proposed:

```python
class Order(BaseModel):
    instrument: Instrument  # always present in public model
```

Alternative if broker payloads cannot always provide this:

```python
class BrokerOrder(BaseModel): ...
class Order(BaseModel): ...  # public, canonical, fully resolved
```

Why this is more elegant:
- Public model invariants are stable and trustworthy.
- Callers do not need defensive `None` handling for core identity fields.

### 4) Error Semantics: Generic Failure Buckets vs Typed Bulk Results

Current:

```python
cancelled, failed = [], []
for order in open_orders:
    try:
        await self._adapter.cancel_order(order.id)
        cancelled.append(order.id)
    except Exception:
        failed.append(order.id)
```

Proposed:

```python
class BulkItemResult(BaseModel):
    id: str
    ok: bool
    error_type: str | None = None
    error_message: str | None = None

class BulkCancelResult(BaseModel):
    items: list[BulkItemResult]
```

Why this is more elegant:
- Failure semantics are explicit and inspectable.
- Prevents silent loss of error context.

### 5) Adapter Registration: Import Side Effects vs Explicit Registry

Current:

```python
# tt_connect/__init__.py
import tt_connect.adapters.zerodha.adapter
import tt_connect.adapters.angelone.adapter
```

Proposed:

```python
# tt_connect/registry.py
REGISTRY: dict[str, type[BrokerAdapter]] = {
    "zerodha": ZerodhaAdapter,
    "angelone": AngelOneAdapter,
}
```

Why this is more elegant:
- Startup behavior is explicit.
- Easier dependency control and testing.
- Fewer surprising import-order bugs.

### 6) Interface Typing: Implicit Contracts vs Protocols

Current:

```python
@property
@abstractmethod
def transformer(self) -> Any: ...
```

Proposed:

```python
class Transformer(Protocol):
    def to_order_params(...) -> dict[str, Any]: ...
    def to_modify_params(self, req: ModifyOrderRequest) -> dict[str, Any]: ...
    def to_order(self, raw: dict[str, Any], instrument: Instrument) -> Order: ...
    def parse_error(self, raw: dict[str, Any]) -> TTConnectError: ...
```

Why this is more elegant:
- Contracts are explicit and machine-checkable.
- Extension points become stable and easier to implement correctly.

### 7) State Guards: Asserts vs Explicit State Machine

Current:

```python
assert self._resolver, "Call await broker.init() first"
```

Proposed:

```python
class ClientState(StrEnum):
    CREATED = "created"
    CONNECTED = "connected"
    CLOSED = "closed"

def _require_connected(self) -> None:
    if self._state != ClientState.CONNECTED:
        raise TTConnectError("Client must be connected before this operation")
```

Why this is more elegant:
- Runtime behavior is explicit and user-facing.
- Better errors, no reliance on Python assert behavior.

## Refactor Roadmap (Minimal Breakage)

Phase 1: Explicit lifecycle without breaking existing users.
- Add `connect()` and context managers to sync + async clients.
- Keep constructor auto-connect temporarily, but mark as deprecated behavior.
- Add sync `close()` to stop internal loop thread cleanly.

Phase 2: Canonical request objects.
- Introduce `PlaceOrderRequest` and `ModifyOrderRequest`.
- Keep old signatures as compatibility wrappers.
- Emit deprecation warnings for broker-native kwargs paths.

Phase 3: Typed boundaries and state model.
- Introduce `Protocol` contracts for transformer and adapter boundaries.
- Replace `assert` lifecycle checks with explicit state guards.
- Eliminate broad `Any` where practical.

Phase 4: Error and result semantics.
- Replace tuple/list bulk return values with typed bulk result models.
- Preserve original broker error metadata in normalized error objects.

Phase 5: Model invariants and registry cleanup.
- Ensure public `Order` model always has canonical instrument identity.
- Move to explicit adapter registry and remove import-driven registration.

## Acceptance Criteria

The design should be considered "elegant enough" when:

1. No public API method requires broker-specific kwargs.
2. No public lifecycle surprises exist (`__init__` has no network I/O).
3. Public models expose stable invariants (no core identity as optional).
4. Bulk operations return typed, inspectable results with error context.
5. Adapter wiring is explicit and deterministic.
6. State violations produce explicit domain errors, never bare asserts.

## Non-Goals

- Rewriting broker parsers that are already correct.
- Replacing async-first architecture.
- Forcing immediate breaking changes without compatibility path.

## Concrete File-Level Solution

This is the implementation-level plan to fix the least elegant files with
minimal regression risk.

### 1) Decompose client orchestration

Current hotspot:
- `tt_connect/client.py`

Action:
- split into focused modules:
  - `tt_connect/lifecycle.py` (connect/close/state machine)
  - `tt_connect/orders.py` (canonical order commands)
  - `tt_connect/portfolio.py` (holdings/positions/trades reads)
  - `tt_connect/sync_client.py` (sync bridge only)
- add explicit `close()` on sync client to stop loop thread deterministically.

### 2) Replace leaky public order APIs

Current hotspot:
- `modify_order(order_id, **kwargs)` in `tt_connect/client.py`

Action:
- introduce canonical request models:
  - `PlaceOrderRequest`
  - `ModifyOrderRequest`
  - `CancelOrderRequest`
- adapters translate canonical request models into broker-native payloads.
- keep old kwargs signatures only as short-lived compatibility wrappers.

### 3) Enforce explicit client state

Current hotspot:
- runtime `assert` guards in `tt_connect/client.py` and
  `tt_connect/instrument_manager/manager.py`

Action:
- introduce explicit state machine:
  - `CREATED`, `CONNECTED`, `CLOSED`
- replace `assert` with domain errors:
  - `ClientNotConnectedError`
  - `InvalidStateError`

### 4) Strengthen public model invariants

Current hotspot:
- `Order.instrument: Instrument | None` in `tt_connect/models.py`

Action:
- make public `Order.instrument` mandatory.
- if broker payloads are incomplete, use internal raw model (e.g. `BrokerOrder`)
  and enrich before returning public `Order`.

### 5) Split AngelOne websocket monolith

Current hotspot:
- `tt_connect/ws/angelone.py`

Action:
- split responsibilities into:
  - `tt_connect/ws/angelone/connection.py` (socket lifecycle/reconnect)
  - `tt_connect/ws/angelone/protocol.py` (subscribe/unsubscribe payloads)
  - `tt_connect/ws/angelone/parser.py` (binary packet decoding)
- remove direct access to auth private fields by introducing typed auth/session
  access contract.

### 6) Tighten adapter contracts and registration

Current hotspot:
- loose typing and auto-registration in `tt_connect/adapters/base.py`
- import side effects in `tt_connect/__init__.py`

Action:
- replace `Any` extension points with typed protocols:
  - `Transformer`
  - `ParsedInstruments`
- keep `_request` transport-focused and delegate broker error mapping via typed
  hook.
- remove import side-effect registration and move to explicit plugin registry /
  entry-point loading.

### 7) Shrink instrument manager responsibilities

Current hotspot:
- `tt_connect/instrument_manager/manager.py`

Action:
- split into:
  - `tt_connect/instrument_manager/refresh_policy.py` (staleness + on_stale)
  - `tt_connect/instrument_manager/writer.py` (insert/write logic)
  - `tt_connect/instrument_manager/manager.py` (thin orchestration)

## Execution Order (Least Regression)

1. Add explicit state handling and sync `close()`.
2. Add canonical request models with compatibility wrappers.
3. Split websocket file without behavior changes.
4. Split instrument manager without behavior changes.
5. Enforce strict public `Order` invariant.
6. Cut over to plugin-based adapter registration.

## Why This Matters

This package sells portability and predictability. Elegance is not aesthetic
here; it is operational safety. The API must feel inevitable so users can trust
it under real trading workflows without needing to memorize internals.
