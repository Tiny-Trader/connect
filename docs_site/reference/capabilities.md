# Broker Capabilities

## Zerodha
- Auth modes: `manual`
- Segments: `NSE`, `BSE`, `NFO`, `BFO`, `CDS`
- Order types: `MARKET`, `LIMIT`, `SL`, `SL_M`
- Product types: `CNC`, `MIS`, `NRML`

## AngelOne
- Auth modes: `manual`, `auto`
- Segments: `NSE`, `BSE`, `NFO`, `CDS`, `MCX`
- Order types: `MARKET`, `LIMIT`, `SL`, `SL_M`
- Product types: `CNC`, `MIS`, `NRML`

## Capability checks in order flow
Before placing an order, the library validates:
- segment support
- order type support
- product type support
- instrument is tradeable (index instruments are not tradeable)

## Related guides
- [Broker Differences](../broker-differences.md)
- [Orders](../orders.md)
- [GTT](../gtt.md)
