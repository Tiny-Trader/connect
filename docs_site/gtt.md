# GTT (Trigger Orders)

## What GTT means
A rule that triggers an order when price condition is met.

## Create a single-leg GTT
```python
from tt_connect import TTConnect, GttLeg
from tt_connect.instruments import Equity
from tt_connect.enums import Exchange, Side, ProductType

config = {"api_key": "...", "access_token": "..."}

with TTConnect("zerodha", config) as broker:
    gtt_id = broker.place_gtt(
        instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
        last_price=800.0,
        legs=[
            GttLeg(
                trigger_price=790.0,
                price=789.5,
                side=Side.BUY,
                qty=1,
                product=ProductType.CNC,
            )
        ],
    )
    print("GTT ID:", gtt_id)
```

## Read and modify GTT
```python
with TTConnect("zerodha", config) as broker:
    gtt = broker.get_gtt("123456")
    print(gtt.gtt_id, gtt.status, gtt.symbol)

    broker.modify_gtt(
        gtt_id="123456",
        instrument=Equity(exchange=Exchange.NSE, symbol="SBIN"),
        last_price=805.0,
        legs=[
            GttLeg(
                trigger_price=792.0,
                price=791.5,
                side=Side.BUY,
                qty=1,
                product=ProductType.CNC,
            )
        ],
    )
```

## Cancel GTT
```python
with TTConnect("zerodha", config) as broker:
    broker.cancel_gtt("123456")
```

## Practical notes
- GTT behavior is broker-specific
- always confirm trigger status after creation
- some brokers support richer GTT forms than others

## See also
- [Client methods (GTT APIs)](reference/clients.md)
- [Models (`Gtt`, `GttLeg`)](reference/models.md)
- [Broker capabilities](reference/capabilities.md)
- [Broker operation notes](reference/operation-notes.md)
