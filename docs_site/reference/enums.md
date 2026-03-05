# Enums

## Enum table

| Enum | Values | Typical usage |
|---|---|---|
| `Exchange` | `NSE`, `BSE`, `NFO`, `BFO`, `CDS`, `MCX` | Instrument exchange/segment |
| `OptionType` | `CE`, `PE` | Option side |
| `ProductType` | `CNC`, `MIS`, `NRML` | Order product/margin type |
| `OrderType` | `MARKET`, `LIMIT`, `SL`, `SL_M` | Order execution style |
| `Side` | `BUY`, `SELL` | Order direction |
| `OrderStatus` | `PENDING`, `OPEN`, `COMPLETE`, `CANCELLED`, `REJECTED` | Normalized order state |
| `OnStale` | `fail`, `warn` | Instrument cache staleness behavior |
| `AuthMode` | `manual`, `auto` | Broker login mode |
| `ClientState` | `created`, `connected`, `closed` | Client lifecycle state |
| `CandleInterval` | `1minute`, `3minute`, `5minute`, `10minute`, `15minute`, `30minute`, `60minute`, `day` | Historical candle interval |

## Related guides
- [Orders](../orders.md)
- [Instruments](../instruments.md)
- [Login & Session](../login-and-session.md)
- [Market Data](../market-data.md)
