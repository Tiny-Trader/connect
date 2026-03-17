# Recipe: Stream and Store Live Ticks

This example streams ticks and writes simple CSV rows.

```python
import asyncio
from pathlib import Path
from tt_connect import AsyncTTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange
from tt_connect import Tick

OUT = Path("ticks.csv")

async def on_tick(tick: Tick) -> None:
    row = f"{tick.timestamp},{tick.instrument.exchange},{tick.instrument.symbol},{tick.ltp},{tick.volume},{tick.oi}\n"
    with OUT.open("a", encoding="utf-8") as f:
        f.write(row)

async def main() -> None:
    config = {"api_key": "...", "access_token": "..."}
    watch = [
        Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        Equity(exchange=Exchange.NSE, symbol="SBIN"),
    ]

    async with AsyncTTConnect("zerodha", config) as broker:
        await broker.subscribe(watch, on_tick)
        await asyncio.sleep(30)
        await broker.unsubscribe(watch)

asyncio.run(main())
```

## Practical note
For high tick rates, use an in-memory queue + background writer instead of writing per tick.

## Related reference
- [Client methods (`subscribe`, `unsubscribe`)](../reference/clients.md)
- [Models (`Tick`)](../reference/models.md)
- [Broker operation notes](../reference/operation-notes.md)
