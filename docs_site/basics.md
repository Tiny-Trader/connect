# Basics

## What this package does
`tt-connect` gives one common API over broker APIs.

You write one trading flow, then switch brokers by changing client config.

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

## First working script (sync)
```python
from tt_connect import TTConnect

config = {
    "api_key": "YOUR_API_KEY",
    "access_token": "YOUR_ACCESS_TOKEN",
}

with TTConnect("zerodha", config) as broker:
    profile = broker.get_profile()
    funds = broker.get_funds()

    print(profile.client_id, profile.name)
    print("Available funds:", funds.available)
```

## Async version
```python
import asyncio
from tt_connect import AsyncTTConnect

async def main() -> None:
    config = {
        "api_key": "YOUR_API_KEY",
        "access_token": "YOUR_ACCESS_TOKEN",
    }

    async with AsyncTTConnect("zerodha", config) as broker:
        profile = await broker.get_profile()
        print(profile.client_id, profile.name)

asyncio.run(main())
```

## Quick path
1. Configure credentials
2. Create client
3. Fetch profile/funds
4. Place order
5. Track order/trade/position

## See also
- [Client methods](reference/clients.md)
- [Models](reference/models.md)
- [Enums](reference/enums.md)
