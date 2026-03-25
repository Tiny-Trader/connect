# Recipe: Recover From Reconnect During Market Hours

The WebSocket client reconnects automatically. Use `on_stale` and `on_recovered` to
react when data stops flowing and when it resumes — no manual timestamp tracking needed.

```python
import asyncio
from tt_connect import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange
from tt_connect import Tick

algo_active = True

async def on_tick(tick: Tick) -> None:
    if not algo_active:
        return
    print(tick.instrument.symbol, tick.ltp)

async def on_stale() -> None:
    global algo_active
    algo_active = False
    print("Feed stale — algo paused")

async def on_recovered() -> None:
    global algo_active
    algo_active = True
    print("Feed recovered — algo resumed")

async def main() -> None:
    config = {"api_key": "...", "access_token": "..."}
    watch = [Equity(exchange=Exchange.NSE, symbol="RELIANCE")]

    async with AsyncTTConnect("zerodha", config) as broker:
        await broker.subscribe(
            watch,
            on_tick,
            on_stale=on_stale,
            on_recovered=on_recovered,
        )
        await asyncio.sleep(120)

asyncio.run(main())
```

## How it works

| Event | When | What to do |
|---|---|---|
| `on_stale` | No tick for 30 seconds | Pause algo, alert, stop placing orders |
| `on_recovered` | First tick after stale period | Resume algo, resync state if needed |

Both fire across reconnects — you do not need to re-subscribe after a disconnect.

## Tips

- Do not assume tick ordering is preserved across a reconnect boundary
- If your strategy holds state per tick (e.g. running VWAP), resync it in `on_recovered`
- `broker.last_tick_at(instrument)` gives the exact wall-clock time of the last received tick if you need finer control

## What's next?
- [Safety & Good Practices](../safety-and-good-practices.md) — production checklist for live trading
- [Broker Differences](../broker-differences.md) — understand per-broker WebSocket behavior

## Related reference

- [Realtime (WebSocket)](../realtime-websocket.md)
- [Client methods (`subscribe`, `feed_state`, `last_tick_at`)](../reference/clients.md)
- [Enums (`FeedState`)](../reference/enums.md)
- [Troubleshooting: WebSocket reconnect](../troubleshooting/websocket-reconnect.md)
