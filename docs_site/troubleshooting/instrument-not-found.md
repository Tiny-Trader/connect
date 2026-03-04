# Instrument Not Found

## Common symptoms
- `InstrumentNotFoundError`
- order/quote call fails for specific symbol+expiry+strike

## Fast checks
1. Verify exchange is correct (`NSE`, `BSE`, etc.).
2. Verify symbol spelling exactly.
3. For derivatives, verify expiry/strike/CE-PE exactly.
4. Use search/helper APIs before placing order.

## Debug pattern
```python
from tt_connect import TTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    print(broker.search_instruments("SBIN", exchange="NSE"))
    underlying = Equity(exchange=Exchange.NSE, symbol="SBIN")
    print(broker.get_expiries(underlying))
```

## Common root causes
- wrong exchange
- stale/invalid derivative contract values
- typo in symbol

## Related
- [Instruments](../instruments.md)
- [Models](../reference/models.md)
- [Client methods](../reference/clients.md)
