# Broker Capabilities

## Capability matrix

| Capability | Zerodha | AngelOne |
|---|---|---|
| Auth modes | `manual` | `manual`, `auto` |
| Segments | `NSE`, `BSE`, `NFO`, `BFO`, `CDS` | `NSE`, `BSE`, `NFO`, `CDS`, `MCX` |
| Order types | `MARKET`, `LIMIT`, `SL`, `SL_M` | `MARKET`, `LIMIT`, `SL`, `SL_M` |
| Product types | `CNC`, `MIS`, `NRML` | `CNC`, `MIS`, `NRML` |

## Pre-order validation checks

| Check | What is validated |
|---|---|
| Segment check | Instrument exchange is supported by broker |
| Order type check | Requested order type is allowed |
| Product check | Requested product type is allowed |
| Tradeability check | Index instruments are blocked for order placement |

## Practical guidance
- Validate capability-sensitive flows in integration tests per broker.
- Keep fallback behavior for broker-specific endpoint differences.
- For strategy portability, treat broker differences as expected behavior.

## Related guides
- [Broker Differences](../broker-differences.md)
- [Broker operation notes](operation-notes.md)
- [Orders](../orders.md)
- [GTT](../gtt.md)
