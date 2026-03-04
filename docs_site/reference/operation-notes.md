# Broker Operation Notes

This page lists behavior differences that matter in real user flows.

## Orders and order book

| Operation | Zerodha | AngelOne | What you should do |
|---|---|---|---|
| `get_order(order_id)` | Supported | Not supported as single-order endpoint | Use `get_orders()` and filter by `order_id` for AngelOne |
| `get_orders()` | Returns full order book | Returns normalized list (empty list when broker returns null) | Always handle empty list safely |
| `cancel_all_orders()` | Works through list + cancel flow | Works through list + cancel flow | Capture both `cancelled` and `failed` IDs |

## GTT

| Operation | Zerodha | AngelOne | What you should do |
|---|---|---|---|
| `place_gtt` | Supported | Supported | Keep payload simple and broker-compatible |
| `modify_gtt` | Supported | Supported | Re-fetch rule after modify |
| `cancel_gtt` | Direct cancel by id | Uses rule details internally before cancel | Handle broker errors and retry only when transient |
| `get_gtts` | Returns list | Normalized to list even when broker gives dict/null | Treat response as list in user code |

## Auth/session

| Area | Zerodha | AngelOne | What you should do |
|---|---|---|---|
| Auth modes | `manual` only | `manual` + `auto` | Pick mode per broker capability |
| Token lifecycle | Access token expected from external login flow | Auto mode supports TOTP login + renew path | Use `cache_session` where appropriate |

## Market data (REST)

| Operation | Zerodha | AngelOne | What you should do |
|---|---|---|---|
| `get_quotes` | Supported | Not currently supported in adapter as REST quotes call | Prefer WebSocket for AngelOne live quote use cases |
| `get_historical` | Supported | Supported | Use same canonical candle request path |

## WebSocket streaming

| Area | Zerodha | AngelOne | What you should do |
|---|---|---|---|
| Subscribe mode | Uses full mode for richer fields | Uses snap-quote mode for richer fields | Keep callback tolerant to missing fields |
| Reconnect | Auto reconnect + resubscribe | Auto reconnect + resubscribe | Keep callback idempotent and fast |

## Instrument and capability checks

| Check | Behavior |
|---|---|
| Segment/order/product validation | Checked before order placement |
| Index tradeability | Index instruments are blocked for order placement |
| Instrument resolution | Canonical instrument is mapped to broker token/symbol before call |

## Related guides
- [Broker Differences](../broker-differences.md)
- [Orders](../orders.md)
- [GTT](../gtt.md)
- [Market Data](../market-data.md)
