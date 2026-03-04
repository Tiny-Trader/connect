# Broker Differences

## Why this page matters
API shape is unified, but broker behavior is not always identical.

## Differences to track
- supported auth modes
- supported segments/order/product types
- GTT support details
- quote/historical/stream field depth

## Recommended approach
- check capability before critical flows
- keep broker-specific fallbacks for edge cases
- test same strategy on each broker separately
