# Holdings & Funds

## Holdings vs positions
- Holdings: delivery/carry inventory
- Positions: open trading exposure

## Read funds
```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    f = broker.get_funds()
    print("Available:", f.available)
    print("Used:", f.used)
    print("Total:", f.total)
    print("Collateral:", f.collateral)
```

## Read holdings
```python
with TTConnect("zerodha", config) as broker:
    holdings = broker.get_holdings()
    for h in holdings:
        print(
            h.instrument.exchange,
            h.instrument.symbol,
            "qty=", h.qty,
            "avg=", h.avg_price,
            "ltp=", h.ltp,
            "pnl=", h.pnl,
            "pnl%=", h.pnl_percent,
        )
```

## Quick usage idea
- use funds check before placing orders
- use holdings for delivery portfolio reporting
- use positions for intraday risk/exposure tracking

## User expectations
- values can change quickly during market hours
- field names are normalized, but broker math may differ

## See also
- [Client methods (`get_holdings`, `get_funds`)](reference/clients.md)
- [Models (`Holding`, `Fund`)](reference/models.md)
