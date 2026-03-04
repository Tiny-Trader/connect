# Instruments

## Supported instrument types
- Stock (equity)
- Future
- Option
- Index (mainly for market data and underlying reference)

## Important fields
- exchange
- symbol
- expiry (for futures/options)
- strike + option type CE/PE (for options)

## Create instrument objects
```python
from datetime import date
from tt_connect.instruments import Equity, Future, Option, Index
from tt_connect.enums import Exchange, OptionType

reliance = Equity(exchange=Exchange.NSE, symbol="RELIANCE")
nifty_index = Index(exchange=Exchange.NSE, symbol="NIFTY")

nifty_fut = Future(
    exchange=Exchange.NSE,
    symbol="NIFTY",
    expiry=date(2026, 3, 26),
)

nifty_ce = Option(
    exchange=Exchange.NSE,
    symbol="NIFTY",
    expiry=date(2026, 3, 26),
    strike=22000.0,
    option_type=OptionType.CE,
)
```

## Search instruments
```python
from tt_connect import TTConnect

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    results = broker.search_instruments("RELIANCE", exchange="NSE")
    for i in results:
        print(i.exchange, i.symbol)
```

## Discover futures/options/expiries
```python
from tt_connect import TTConnect
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange

config = {"api_key": "...", "access_token": "..."}
underlying = Equity(exchange=Exchange.NSE, symbol="SBIN")

with TTConnect("zerodha", config) as broker:
    expiries = broker.get_expiries(underlying)
    print("Expiries:", expiries)

    futures = broker.get_futures(underlying)
    print("Futures count:", len(futures))

    if expiries:
        chain = broker.get_options(underlying, expiry=expiries[0])
        print("Options for first expiry:", len(chain))
```

## Instrument matching
You pass a canonical instrument. The package maps it to broker token/symbol before API calls.

## User tips
- always use correct exchange + symbol
- use helper APIs to discover futures/options/expiries
- treat index as non-tradable for order placement

## See also
- [Client methods (`get_futures`, `get_options`, `get_expiries`, `search_instruments`)](reference/clients.md)
- [Models (Instrument, Equity, Future, Option, Index)](reference/models.md)
- [Enums (`Exchange`, `OptionType`)](reference/enums.md)
