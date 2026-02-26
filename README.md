# tt-connect

`tt-connect` is a unified Python broker API for Indian markets. It gives you one canonical interface for auth, instruments, orders, portfolio, and reports across brokers.

## Who This Is For

- Trading system developers who want broker portability.
- Teams building execution, monitoring, or portfolio services.
- Contributors extending broker support and reliability.

## Installation

```bash
cd connect
poetry install
```

## Quick Start

```python
from tt_connect import TTConnect, PlaceOrderRequest
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

with TTConnect("zerodha", {"api_key": "...", "access_token": "..."}) as broker:
    req = PlaceOrderRequest(
        instrument=Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        side=Side.BUY,
        qty=1,
        order_type=OrderType.MARKET,
        product=ProductType.CNC,
    )
    order_id = broker.place_order(req)
    print(order_id)
```

## Broker Capability Snapshot

| Capability | Zerodha | AngelOne |
|---|---|---|
| Auth modes | Manual | Manual + Auto |
| Profile/Funds/Holdings/Positions | Yes | Yes |
| Orders (place/modify/cancel/list) | Yes | Yes |
| Trades | Yes | Yes |
| Instrument fetch + resolve | Yes | Yes |
| Streaming (WebSocket) | Yes | Yes |
| GTT orders | Yes | Yes |
| Margin calculator API | Planned | Planned |

## Documentation

- User docs: [docs/README.md](./docs/README.md)
- Getting started: [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md)
- Contributor docs: [CONTRIBUTING.md](./CONTRIBUTING.md), [docs/CONTRIBUTOR_GUIDE.md](./docs/CONTRIBUTOR_GUIDE.md)
- Architecture internals: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

## Development Commands

```bash
make lint
make typecheck
make test-fast
make coverage
```

## Legal and Risk Notices

- [DISCLAIMER.md](./DISCLAIMER.md)
- [SECURITY.md](./SECURITY.md)
- [COMPLIANCE.md](./COMPLIANCE.md)
- [TRADEMARK.md](./TRADEMARK.md)
- [LICENSE](./LICENSE)
