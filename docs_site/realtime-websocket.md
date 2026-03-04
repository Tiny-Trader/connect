# Realtime (WebSocket)

Use `AsyncTTConnect` for WebSocket subscribe/unsubscribe.

## Minimal example
```python
import asyncio
from tt_connect import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange
from tt_connect.models import Tick

async def on_tick(tick: Tick) -> None:
    print(tick.instrument.symbol, tick.ltp, tick.timestamp)

async def main() -> None:
    config = {"api_key": "...", "access_token": "..."}

    async with AsyncTTConnect("zerodha", config) as broker:
        watch = [
            Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
            Equity(exchange=Exchange.NSE, symbol="SBIN"),
        ]
        await broker.subscribe(watch, on_tick)
        await asyncio.sleep(30)
        await broker.unsubscribe(watch)

asyncio.run(main())
```

## Reliability behavior
- reconnect is automatic
- tracked subscriptions are restored after reconnect

## Callback best practices
- keep callback fast and non-blocking
- push heavy work to queue/worker
- catch your own business logic errors in callback

## See also
- [Client methods (`subscribe`, `unsubscribe`)](reference/clients.md)
- [Models (`Tick`)](reference/models.md)
- [Recipe: Stream and store live ticks](recipes/stream-and-store-live-ticks.md)
- [Recipe: Recover from reconnect](recipes/recover-from-reconnect.md)
- [Troubleshooting: WebSocket reconnect](troubleshooting/websocket-reconnect.md)
