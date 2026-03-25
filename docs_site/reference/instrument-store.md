# InstrumentStore

`InstrumentStore` and `AsyncInstrumentStore` provide **read-only** access to the local instrument cache without authenticating with a broker.

Use them when you need instrument discovery, metadata, or option-chain browsing without placing trades.

!!! note "Seed the DB first"
    The store reads from a local SQLite DB that is populated by `TTConnect` / `AsyncTTConnect` during `init()`. If the DB has not been seeded yet, store initialization will fail with a clear error.

## Quick example

=== "Sync"

    ```python
    from tt_connect import InstrumentStore
    from tt_connect.instruments import Index, Future, Option
    from tt_connect.enums import Exchange

    with InstrumentStore("zerodha") as store:
        # Search by symbol
        results = store.search("NIFTY")

        # List expiries
        nifty = Index(exchange=Exchange.NSE, symbol="NIFTY")
        expiries = store.get_expiries(nifty)

        # Get metadata
        info = store.get_instrument_info(nifty)
        print(f"Lot size: {info.lot_size}, Tick size: {info.tick_size}")

        # Option chain
        chain = store.get_option_chain(nifty, expiries[0])
        for entry in chain.entries[:5]:
            print(f"  {entry.strike}  CE={entry.ce}  PE={entry.pe}")
    ```

=== "Async"

    ```python
    from tt_connect import AsyncInstrumentStore
    from tt_connect.instruments import Index
    from tt_connect.enums import Exchange

    async with AsyncInstrumentStore("zerodha") as store:
        nifty = Index(exchange=Exchange.NSE, symbol="NIFTY")
        expiries = await store.get_expiries(nifty)
        chain = await store.get_option_chain(nifty, expiries[0])
    ```

## Constructor

| Class | Signature | Notes |
|---|---|---|
| Sync | `InstrumentStore(broker: str)` | Opens DB and starts background event loop |
| Async | `AsyncInstrumentStore(broker: str)` | Call `await init()` or use `async with` |

Both support context managers (`with` / `async with`) for automatic cleanup.

## Methods

| Method | Params | Returns | Description |
|---|---|---|---|
| `list_instruments` | `instrument_type=None, exchange=None, underlying=None, expiry=None, option_type=None, strike=None, strike_min=None, strike_max=None, has_derivatives=None, limit=100` | `list[Instrument]` | Filter instruments with any combination of criteria |
| `get_expiries` | `instrument: Instrument` | `list[date]` | All distinct expiry dates for an underlying |
| `search` | `query: str, exchange: str | None = None` | `list[Equity | Index]` | Search underlyings by symbol substring |
| `get_instrument_info` | `instrument: Instrument` | `InstrumentInfo` | Metadata: lot size, tick size, segment, name |
| `get_option_chain` | `underlying: Instrument, expiry: date` | `OptionChain` | CE/PE pairs for all strikes at a given expiry |
| `execute` | `sql: str, params: tuple = ()` | `list[tuple]` | Raw SQL escape hatch against the local DB |
| `close` | none | `None` | Close the DB connection |

## Return types

### InstrumentInfo

| Field | Type | Description |
|---|---|---|
| `instrument` | `Instrument` | The resolved instrument |
| `name` | `str | None` | Human-readable name |
| `lot_size` | `int` | Trading lot size |
| `tick_size` | `float` | Minimum price increment |
| `segment` | `str` | Market segment |

### OptionChain

| Field | Type | Description |
|---|---|---|
| `underlying` | `Instrument` | The underlying instrument |
| `expiry` | `date` | Expiry date |
| `entries` | `list[OptionChainEntry]` | Strikes sorted ascending |

### OptionChainEntry

| Field | Type | Description |
|---|---|---|
| `strike` | `float` | Strike price |
| `ce` | `Option | None` | Call option at this strike |
| `pe` | `Option | None` | Put option at this strike |

## When to use InstrumentStore vs TTConnect

| | `TTConnect` | `InstrumentStore` |
|---|---|---|
| Authenticates | Yes | No |
| Refreshes instrument data | Yes (on `init()`) | No |
| Place orders | Yes | No |
| Instrument discovery | Yes (`get_futures`, `get_options`, `get_expiries`) | Yes (same + `list_instruments`, `search`, `get_option_chain`) |
| Raw SQL | No | Yes (`execute`) |
| Use case | Trading | Research, strategy tooling, option chain analysis |

## Related

- [Instruments guide](../instruments.md)
- [Example: `examples/angelone_store.py`](https://github.com/Tiny-Trader/connect/blob/main/examples/angelone_store.py)
