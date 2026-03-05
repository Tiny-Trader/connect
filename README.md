# tt-connect

[![CI](https://github.com/Tiny-Trader/connect/actions/workflows/connect-ci.yml/badge.svg?branch=main)](https://github.com/Tiny-Trader/connect/actions/workflows/connect-ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/tt-connect.svg)](https://pypi.org/project/tt-connect/)
[![Python](https://img.shields.io/pypi/pyversions/tt-connect.svg)](https://pypi.org/project/tt-connect/)
[![License](https://img.shields.io/github/license/Tiny-Trader/connect.svg)](https://github.com/Tiny-Trader/connect/blob/main/LICENSE)

`tt-connect` is a unified Python broker API for Indian markets. It gives you one canonical interface for auth, instruments, orders, portfolio, and reports across brokers.

## Who This Is For

- Trading system developers who want broker portability
- Teams building execution, monitoring, or portfolio services
- Contributors extending broker support and reliability

## Quick Start

```bash
cd connect
poetry install
```

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

## Documentation

| Guide | Description |
|-------|-------------|
| **[Quick Start](docs/QUICKSTART.md)** | Get installed and place your first order in 5 minutes |
| **[Examples](docs/EXAMPLES.md)** | Complete working code for Zerodha and AngelOne |
| [Contributor Guide](docs/CONTRIBUTOR_GUIDE.md) | Local setup, testing, implementation workflow |
| [Architecture](docs/ARCHITECTURE.md) | System design and internals |

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
| Margin calculator API | Not supported | Not supported |

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
