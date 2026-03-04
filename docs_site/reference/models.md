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

## Request models

| Model | Required fields | Optional/default fields | Used by |
|---|---|---|---|
| `PlaceOrderRequest` | `instrument`, `side`, `qty`, `order_type`, `product` | `price=None`, `trigger_price=None`, `tag=uuid` | `place_order` |
| `ModifyOrderRequest` | `order_id` | `qty=None`, `price=None`, `trigger_price=None`, `order_type=None` | `modify_order` |
| `GttLeg` | `trigger_price`, `price`, `side`, `qty`, `product` | none | GTT request/response leg |
| `PlaceGttRequest` | `instrument`, `last_price`, `legs` | none | `place_gtt` |
| `ModifyGttRequest` | `gtt_id`, `instrument`, `last_price`, `legs` | none | `modify_gtt` |
| `GetHistoricalRequest` | `instrument`, `interval`, `from_date`, `to_date` | `include_oi=True` | Internal request mapping |

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
| Request models | Mutable |
| Most response models | Frozen/read-only |

## Related guides
- [Instruments](../instruments.md)
- [Orders](../orders.md)
- [Market Data](../market-data.md)
- [GTT](../gtt.md)
