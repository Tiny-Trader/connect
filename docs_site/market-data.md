# Market Data

## Data types
- Quotes: snapshot from REST
- Ticks: live updates from WebSocket
- Candles: historical OHLC bars

## Tick fields you may see
- ltp
- volume
- oi
- bid/ask
- timestamp

## Practical guidance
- use quotes for periodic checks
- use WebSocket for low-latency flows
- use candles for strategy backfill and analytics

## Reality checks
- some fields may be missing by broker or segment
- timestamps may differ from local clock
