# Enums

## Public enums

Import from `tt_connect.enums`:

| Enum | Values | Typical usage |
|---|---|---|
| `Exchange` | `NSE`, `BSE`, `NFO`, `BFO`, `CDS`, `MCX` | Instrument exchange/segment |
| `OptionType` | `CE`, `PE` | Option side |
| `ProductType` | `CNC`, `MIS`, `NRML` | Order product/margin type |
| `OrderType` | `MARKET`, `LIMIT`, `SL`, `SL_M` | Order execution style |
| `Side` | `BUY`, `SELL` | Order direction |
| `OrderStatus` | `PENDING`, `OPEN`, `COMPLETE`, `CANCELLED`, `REJECTED` | Normalized order state |
| `FeedState` | `connecting`, `connected`, `reconnecting`, `stale`, `closed` | WebSocket feed health state |
| `CandleInterval` | `1minute`, `3minute`, `5minute`, `10minute`, `15minute`, `30minute`, `60minute`, `day` | Historical candle interval |

## Internal enums

These are used by config dicts and client internals — do not import them in user code:

| Enum | Used where |
|---|---|
| `OnStale` | `on_stale` config key (`"fail"` or `"warn"`) |
| `AuthMode` | `auth_mode` config key (`"manual"` or `"auto"`) |
| `ClientState` | Internal client lifecycle tracking |

## Related guides
- [Orders](../orders.md)
- [Instruments](../instruments.md)
- [Login & Session](../login-and-session.md)
- [Market Data](../market-data.md)
- [Realtime (WebSocket)](../realtime-websocket.md)
