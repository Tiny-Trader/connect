# Realtime (WebSocket)

Use `AsyncTTConnect` for WebSocket subscribe/unsubscribe.

## Minimal example

```python
import asyncio
from tt_connect import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange
from tt_connect import Tick

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

## Feed health callbacks

Subscribe accepts two optional callbacks that fire when the feed goes silent or recovers:

```python
import asyncio
from tt_connect import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange
from tt_connect import Tick

async def on_tick(tick: Tick) -> None:
    print(tick.instrument.symbol, tick.ltp)

async def on_stale() -> None:
    # No tick received for 30 seconds — alert or pause your algo
    print("Feed is stale — no data")

async def on_recovered() -> None:
    # Ticks are flowing again after a stale period
    print("Feed recovered — resuming")

async def main() -> None:
    config = {"api_key": "...", "access_token": "..."}

    async with AsyncTTConnect("angelone", config) as broker:
        watch = [Equity(exchange=Exchange.NSE, symbol="RELIANCE")]
        await broker.subscribe(
            watch,
            on_tick,
            on_stale=on_stale,
            on_recovered=on_recovered,
        )
        await asyncio.sleep(120)

asyncio.run(main())
```

`on_stale` fires once when the feed crosses the **30-second silence threshold**.
`on_recovered` fires on the first tick after a stale period.

Both callbacks work identically on Zerodha and AngelOne.

## Feed state

Check `broker.feed_state` at any point to read the current stream health:

```python
from tt_connect.enums import FeedState

if broker.feed_state == FeedState.STALE:
    print("No data — market may be closed or connection degraded")

if broker.feed_state == FeedState.CONNECTED:
    print("Stream is healthy")
```

| State | Meaning |
|---|---|
| `CONNECTING` | Initial state before first connect |
| `CONNECTED` | Ticks are flowing normally |
| `STALE` | Connected but no tick for 30+ seconds |
| `RECONNECTING` | Connection lost — reconnect attempt in progress |
| `CLOSED` | Client was closed or `unsubscribe` called |

## Per-instrument last tick time

Check when a specific instrument last produced a tick:

```python
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
age = (datetime.now(IST) - broker.last_tick_at(reliance)).total_seconds()
if age > 60:
    print(f"RELIANCE tick is {age:.0f}s old")
```

Returns `None` if no tick has been received yet for that instrument.

## Reliability behavior

- Reconnect is automatic with exponential backoff (cap: 60 seconds)
- All subscriptions are restored after every reconnect
- `on_stale` / `on_recovered` continue to work across reconnects

## Callback best practices

- Keep callbacks fast and non-blocking
- Push heavy work (DB writes, HTTP calls) to a queue/worker
- Catch your own business logic errors inside callbacks — unhandled exceptions are logged but do not crash the stream

## See also

- [Client methods (`subscribe`, `unsubscribe`, `feed_state`)](reference/clients.md)
- [Enums (`FeedState`)](reference/enums.md)
- [Models (`Tick`)](reference/models.md)
- [Recipe: Stream and store live ticks](recipes/stream-and-store-live-ticks.md)
- [Recipe: Recover from reconnect](recipes/recover-from-reconnect.md)
- [Troubleshooting: WebSocket reconnect](troubleshooting/websocket-reconnect.md)
