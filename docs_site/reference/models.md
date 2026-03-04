# Models

## Instrument models
- `Instrument(exchange, symbol)`
- `Index(exchange, symbol)`
- `Equity(exchange, symbol)`
- `Future(exchange, symbol, expiry)`
- `Option(exchange, symbol, expiry, strike, option_type)`
- `Currency(exchange, symbol)`
- `Commodity(exchange, symbol)`

## Request models
- `PlaceOrderRequest(instrument, side, qty, order_type, product, price=None, trigger_price=None, tag=uuid)`
- `ModifyOrderRequest(order_id, qty=None, price=None, trigger_price=None, order_type=None)`
- `GttLeg(trigger_price, price, side, qty, product)`
- `PlaceGttRequest(instrument, last_price, legs)`
- `ModifyGttRequest(gtt_id, instrument, last_price, legs)`
- `GetHistoricalRequest(instrument, interval, from_date, to_date, include_oi=True)`

## Response models
- `Profile(client_id, name, email, phone=None)`
- `Fund(available, used, total, collateral=0, m2m_unrealized=0, m2m_realized=0)`
- `Holding(instrument, qty, avg_price, ltp, pnl, pnl_percent=0)`
- `Position(instrument, qty, avg_price, ltp, pnl, product)`
- `Order(id, instrument, side, qty, filled_qty, product, order_type, status, price, trigger_price, avg_price, timestamp)`
- `Trade(order_id, instrument, side, qty, avg_price, trade_value, product, timestamp)`
- `Tick(instrument, ltp, volume=None, oi=None, bid=None, ask=None, timestamp=None)`
- `Candle(instrument, timestamp, open, high, low, close, volume, oi=None)`
- `Gtt(gtt_id, status, symbol, exchange, legs)`
- `Margin(total, span, exposure, option_premium=0, final_total, benefit)`

## Mutability rule
- Request models are mutable.
- Most response models are frozen (read-only objects).

## Related guides
- [Instruments](../instruments.md)
- [Orders](../orders.md)
- [Market Data](../market-data.md)
- [GTT](../gtt.md)
