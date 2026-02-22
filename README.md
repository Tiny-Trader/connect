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
from tt_connect import TTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType, OrderType

broker = TTConnect("zerodha", {
    "api_key": "...",
    "access_token": "...",
})

instrument = Equity(exchange=Exchange.NSE, symbol="RELIANCE")
order_id = broker.place_order(
    instrument=instrument,
    qty=1,
    side=Side.BUY,
    product=ProductType.CNC,
    order_type=OrderType.MARKET,
)
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
| Streaming | Not implemented yet | In progress |
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
