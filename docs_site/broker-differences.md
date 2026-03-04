# Broker Differences

## Why this page matters
API shape is unified, but broker behavior is not always identical.

## Current capability snapshot

| Area | Zerodha | AngelOne |
|---|---|---|
| Auth modes | manual | manual, auto |
| Segments | NSE, BSE, NFO, BFO, CDS | NSE, BSE, NFO, CDS, MCX |
| Order types | MARKET, LIMIT, SL, SL_M | MARKET, LIMIT, SL, SL_M |
| Product types | CNC, MIS, NRML | CNC, MIS, NRML |

## Practical difference examples
- Single order fetch may differ by broker behavior/endpoints.
- GTT payload/rules can differ between brokers.
- Market data depth/fields can differ by broker stream mode.

## Recommended approach
- check capability before critical flows
- keep broker-specific fallbacks for edge cases
- test same strategy on each broker separately

## Simple multi-broker pattern
```python
from tt_connect import TTConnect

def print_profile(broker_name: str, config: dict) -> None:
    with TTConnect(broker_name, config) as broker:
        p = broker.get_profile()
        print(broker_name, p.client_id, p.name)
```

## See also
- [Broker capabilities](reference/capabilities.md)
- [Broker operation notes](reference/operation-notes.md)
- [Enums](reference/enums.md)
- [Exceptions](reference/exceptions.md)
