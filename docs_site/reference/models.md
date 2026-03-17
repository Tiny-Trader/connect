# Models

## Instrument models

| Model | Required fields | Optional fields | Notes |
|---|---|---|---|
| `Instrument` | `exchange`, `symbol` | none | Base canonical instrument |
| `Index` | `exchange`, `symbol` | none | Not tradeable for order placement |
| `Equity` | `exchange`, `symbol` | none | Cash market instrument |
| `Future` | `exchange`, `symbol`, `expiry` | none | Derivative keyed by expiry |
| `Option` | `exchange`, `symbol`, `expiry`, `strike`, `option_type` | none | Derivative keyed by strike + CE/PE |
| `Currency` | `exchange`, `symbol` | none | Currency derivative shape |
| `Commodity` | `exchange`, `symbol` | none | Commodity derivative shape |

## GTT leg model

Order methods (`place_order`, `modify_order`, etc.) and GTT methods take keyword arguments
directly — there are no request objects to construct. The one exception is `GttLeg`, which
you compose to describe each leg of a GTT:

| Model | Required fields | Notes |
|---|---|---|
| `GttLeg` | `trigger_price`, `price`, `side`, `qty`, `product` | One entry per GTT leg |

```python
from tt_connect import GttLeg
from tt_connect.enums import Side, ProductType

leg = GttLeg(trigger_price=790.0, price=789.5, side=Side.BUY, qty=1, product=ProductType.CNC)
```

## Response models

| Model | Required fields | Optional/default fields |
|---|---|---|
| `Profile` | `client_id`, `name`, `email` | `phone=None` |
| `Fund` | `available`, `used`, `total` | `collateral=0.0`, `m2m_unrealized=0.0`, `m2m_realized=0.0` |
| `Holding` | `instrument`, `qty`, `avg_price`, `ltp`, `pnl` | `pnl_percent=0.0` |
| `Position` | `instrument`, `qty`, `avg_price`, `ltp`, `pnl`, `product` | none |
| `Order` | `id`, `side`, `qty`, `filled_qty`, `product`, `order_type`, `status` | `instrument=None`, `price=None`, `trigger_price=None`, `avg_price=None`, `timestamp=None` |
| `Trade` | `order_id`, `instrument`, `side`, `qty`, `avg_price`, `trade_value`, `product` | `timestamp=None` |
| `Tick` | `instrument`, `ltp` | `volume=None`, `oi=None`, `bid=None`, `ask=None`, `timestamp=None` |
| `Candle` | `instrument`, `timestamp`, `open`, `high`, `low`, `close`, `volume` | `oi=None` |
| `Gtt` | `gtt_id`, `status`, `symbol`, `exchange`, `legs` | none |
| `Margin` | `total`, `span`, `exposure`, `final_total`, `benefit` | `option_premium=0.0` |

## Mutability

| Model class | Mutability |
|---|---|
| `GttLeg` | Mutable |
| Most response models | Frozen/read-only |

## Related guides
- [Instruments](../instruments.md)
- [Orders](../orders.md)
- [Market Data](../market-data.md)
- [GTT](../gtt.md)
