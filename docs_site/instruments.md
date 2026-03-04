# Instruments

## Supported instrument types
- Stock (equity)
- Future
- Option
- Index (mainly for market data and underlying reference)

## Important fields
- exchange
- symbol
- expiry (for futures/options)
- strike + option type CE/PE (for options)

## Instrument matching
You pass a canonical instrument. The package maps it to broker token/symbol before API calls.

## User tips
- always use correct exchange + symbol
- use helper APIs to discover futures/options/expiries
- treat index as non-tradable for order placement
