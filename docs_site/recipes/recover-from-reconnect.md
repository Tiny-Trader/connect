# Recipe: Recover From Reconnect During Market Hours

The websocket client auto-reconnects. Keep your callback idempotent and stateless.

```python
import asyncio
from tt_connect import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange
from tt_connect.models import Tick

last_seen = {}

async def on_tick(tick: Tick) -> None:
    key = f"{tick.instrument.exchange}:{tick.instrument.symbol}"
    prev = last_seen.get(key)
    last_seen[key] = tick.timestamp
    if prev and tick.timestamp and prev and tick.timestamp < prev:
        # ignore out-of-order tick for simple strategy logic
        return
    print(key, tick.ltp)

async def main() -> None:
    config = {"api_key": "...", "access_token": "..."}
    watch = [Equity(exchange=Exchange.NSE, symbol="RELIANCE")]

    async with AsyncTTConnect("zerodha", config) as broker:
        await broker.subscribe(watch, on_tick)
        await asyncio.sleep(120)

asyncio.run(main())
```

## Tips
- Keep your own latest state per symbol.
- Do not assume strictly ordered ticks across reconnect boundaries.
