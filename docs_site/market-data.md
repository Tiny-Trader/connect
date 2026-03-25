# Market Data

!!! warning "Broker support"
    `get_quotes()` is only available for Zerodha. AngelOne does not expose a REST quotes endpoint — use WebSocket streaming (`subscribe`) instead. `get_historical()` works on both brokers.

## Data types
- Quotes: snapshot from REST
- Ticks: live updates from WebSocket
- Candles: historical OHLC bars

## Get quotes
```python
from tt_connect import TTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    instruments = [
        Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        Equity(exchange=Exchange.NSE, symbol="SBIN"),
    ]
    quotes = broker.get_quotes(instruments)
    for q in quotes:
        print(q.instrument.symbol, q.ltp, q.volume)
```

## Get historical candles
```python
from datetime import datetime, timedelta
from tt_connect.enums import CandleInterval

end = datetime.now()
start = end - timedelta(days=5)

candles = broker.get_historical(
    instrument=Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
    interval=CandleInterval.MINUTE_5,
    from_date=start,
    to_date=end,
)

for c in candles[:3]:
    print(c.timestamp, c.open, c.high, c.low, c.close, c.volume)
```

## Tick fields you may see
- ltp
- volume
- oi
- bid/ask
- timestamp

## Reality checks
- some fields may be missing by broker or segment
- timestamps may differ from your local clock

## What's next?
- [Realtime (WebSocket)](realtime-websocket.md) — stream live ticks with feed health callbacks
- [Recipe: Stream and store live ticks](recipes/stream-and-store-live-ticks.md) — save ticks to CSV

## See also
- [Client methods (`get_quotes`, `get_historical`, `subscribe`)](reference/clients.md)
- [Models (`Tick`, `Candle`)](reference/models.md)
- [Enums (`CandleInterval`)](reference/enums.md)
- [Broker operation notes](reference/operation-notes.md)
