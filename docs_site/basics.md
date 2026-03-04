# Basics

## What this package does
`tt-connect` gives one common API over broker APIs.

## Who it is for
- algo trading developers
- backend services that place orders
- teams that want broker portability

## Common terms
- `Instrument`: what you trade (stock/future/option/index)
- `Order`: intent to buy/sell
- `Trade`: actual fill from an order
- `Position`: current open net quantity
- `Holding`: delivery/carry inventory
- `Tick`: realtime market update

## Quick path
1. Configure credentials
2. Create client
3. Fetch profile/funds
4. Place order
5. Track order/trade/position
