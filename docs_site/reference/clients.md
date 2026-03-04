# Client Methods

## Constructors

### Sync client
```python
TTConnect(broker: str, config: dict[str, Any])
```

### Async client
```python
AsyncTTConnect(broker: str, config: dict[str, Any])
```

## Lifecycle

### `TTConnect`
- `close() -> None`

### `AsyncTTConnect`
- `init() -> None`
- `close() -> None`
- `subscribe(instruments: list[Instrument], on_tick: OnTick) -> None`
- `unsubscribe(instruments: list[Instrument]) -> None`

## Portfolio / Account
- `get_profile() -> Profile`
- `get_funds() -> Fund`
- `get_holdings() -> list[Holding]`
- `get_positions() -> list[Position]`
- `get_trades() -> list[Trade]`
- `get_quotes(instruments: list[Instrument]) -> list[Tick]`
- `get_historical(instrument: Instrument, interval: CandleInterval, from_date: datetime, to_date: datetime) -> list[Candle]`

## Orders
- `place_order(req: PlaceOrderRequest) -> str`
- `modify_order(req: ModifyOrderRequest) -> None`
- `cancel_order(order_id: str) -> None`
- `cancel_all_orders() -> tuple[list[str], list[str]]`
- `get_order(order_id: str) -> Order`
- `get_orders() -> list[Order]`
- `close_all_positions() -> tuple[list[str], list[str]]`

## GTT
- `place_gtt(req: PlaceGttRequest) -> str`
- `modify_gtt(req: ModifyGttRequest) -> None`
- `cancel_gtt(gtt_id: str) -> None`
- `get_gtt(gtt_id: str) -> Gtt`
- `get_gtts() -> list[Gtt]`

## Instrument Helpers
- `get_futures(instrument: Instrument) -> list[Future]`
- `get_options(instrument: Instrument, expiry: date | None = None) -> list[Option]`
- `get_expiries(instrument: Instrument) -> list[date]`
- `search_instruments(query: str, exchange: str | None = None) -> list[Equity]`

## Notes
- `TTConnect` calls async internals in a dedicated background event-loop thread.
- Use `AsyncTTConnect` for websocket-heavy flows.

## Related guides
- [Basics](../basics.md)
- [Orders](../orders.md)
- [Market Data](../market-data.md)
- [Realtime (WebSocket)](../realtime-websocket.md)
