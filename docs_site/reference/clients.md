# Client Methods

## Constructors

| Client | Signature | Notes |
|---|---|---|
| Sync | `TTConnect(broker: str, config: dict[str, Any])` | Initializes and logs in during construction |
| Async | `AsyncTTConnect(broker: str, config: dict[str, Any])` | Call `await init()` before use (or use `async with`) |

## Lifecycle methods

| Client | Method | Params | Returns | Common errors |
|---|---|---|---|---|
| Sync | `close` | none | `None` | `TTConnectError` |
| Async | `init` | none | `None` | `AuthenticationError`, `ConfigurationError`, `TTConnectError` |
| Async | `close` | none | `None` | `TTConnectError` |
| Async | `subscribe` | `instruments`, `on_tick`, `on_stale=None`, `on_recovered=None` | `None` | `ClientNotConnectedError`, `InstrumentNotFoundError`, `TTConnectError` |
| Async | `unsubscribe` | `instruments` | `None` | `ClientNotConnectedError`, `TTConnectError` |
| Async | `feed_state` *(property)* | — | `FeedState` | — |
| Async | `last_tick_at` | `instrument: Instrument` | `datetime \| None` | — |

## Portfolio / account methods

| Method | Params | Returns | Common errors |
|---|---|---|---|
| `get_profile` | none | `Profile` | `ClientNotConnectedError`, `AuthenticationError`, `BrokerError` |
| `get_funds` | none | `Fund` | `ClientNotConnectedError`, `AuthenticationError`, `BrokerError` |
| `get_holdings` | none | `list[Holding]` | `ClientNotConnectedError`, `AuthenticationError`, `BrokerError` |
| `get_positions` | none | `list[Position]` | `ClientNotConnectedError`, `AuthenticationError`, `BrokerError` |
| `get_trades` | none | `list[Trade]` | `ClientNotConnectedError`, `AuthenticationError`, `BrokerError` |
| `get_quotes` | `instruments: list[Instrument]` | `list[Tick]` | `ClientNotConnectedError`, `InstrumentNotFoundError`, `UnsupportedFeatureError` |
| `get_historical` | `instrument`, `interval`, `from_date`, `to_date` | `list[Candle]` | `ClientNotConnectedError`, `InstrumentNotFoundError`, `UnsupportedFeatureError` |

## Order methods

| Method | Params | Returns | Common errors |
|---|---|---|---|
| `place_order` | `instrument, side, qty, order_type, product, price=None, trigger_price=None, tag=None` | `str` (order id) | `UnsupportedFeatureError`, `InstrumentNotFoundError`, `InsufficientFundsError`, `BrokerError` |

!!! note "About `tag`"
    `tag` is an optional client-side correlation ID for tracing orders. If omitted, a UUID is auto-generated. Useful for idempotency checks — pass the same tag and verify via `get_orders()` to detect duplicates before retrying. Sent as `tag` (Zerodha, max 20 chars) or `uniqueorderid` (AngelOne).
| `modify_order` | `order_id, qty=None, price=None, trigger_price=None, order_type=None` | `None` | `OrderNotFoundError`, `InvalidOrderError`, `BrokerError` |
| `cancel_order` | `order_id: str` | `None` | `OrderNotFoundError`, `BrokerError` |
| `cancel_all_orders` | none | `tuple[list[str], list[str]]` | `BrokerError`, `TTConnectError` |
| `get_order` | `order_id: str` | `Order` | `OrderNotFoundError`, `UnsupportedFeatureError`, `BrokerError` |
| `get_orders` | none | `list[Order]` | `BrokerError` |
| `close_all_positions` | none | `tuple[list[str], list[str]]` | `BrokerError`, `TTConnectError` |

## GTT methods

| Method | Params | Returns | Common errors |
|---|---|---|---|
| `place_gtt` | `instrument, last_price, legs: list[GttLeg]` | `str` (gtt id) | `UnsupportedFeatureError`, `InstrumentNotFoundError`, `BrokerError` |
| `modify_gtt` | `gtt_id, instrument, last_price, legs: list[GttLeg]` | `None` | `UnsupportedFeatureError`, `InstrumentNotFoundError`, `BrokerError` |
| `cancel_gtt` | `gtt_id: str` | `None` | `UnsupportedFeatureError`, `BrokerError` |
| `get_gtt` | `gtt_id: str` | `Gtt` | `UnsupportedFeatureError`, `BrokerError` |
| `get_gtts` | none | `list[Gtt]` | `UnsupportedFeatureError`, `BrokerError` |

## Instrument helper methods

| Method | Params | Returns | Common errors |
|---|---|---|---|
| `get_futures` | `instrument: Instrument` | `list[Future]` | `ClientNotConnectedError`, `TTConnectError` |
| `get_options` | `instrument: Instrument`, `expiry: date | None = None` | `list[Option]` | `ClientNotConnectedError`, `TTConnectError` |
| `get_expiries` | `instrument: Instrument` | `list[date]` | `ClientNotConnectedError`, `TTConnectError` |
| `search_instruments` | `query: str`, `exchange: str | None = None` | `list[Equity]` | `ClientNotConnectedError`, `TTConnectError` |

## Notes
- `TTConnect` calls async internals in a dedicated background event-loop thread.
- Use `AsyncTTConnect` for websocket-heavy flows.

## Related guides
- [Basics](../basics.md)
- [Orders](../orders.md)
- [Market Data](../market-data.md)
- [Realtime (WebSocket)](../realtime-websocket.md)
