# Glossary

## Instrument
A tradable entity like stock, future, option, or index.

## Exchange
Market venue/segment identifier like `NSE`, `BSE`, `NFO`.

## Order
Request to buy/sell an instrument.

## Trade (Fill)
Actual execution event generated from an order.

## Position
Current net open quantity for an instrument.

## Holding
Delivery inventory carried in account.

## Product Type
How broker treats margin/holding (`CNC`, `MIS`, `NRML`).

## Order Type
Execution style (`MARKET`, `LIMIT`, `SL`, `SL_M`).

## Tick
Realtime market update from WebSocket.

## Quote
REST snapshot of current market values.

## Candle
OHLC bar for a time interval.

## GTT
Trigger rule that places order when condition is met.

## OCO
One-cancels-other: two trigger legs where one execution cancels the other.

## Access Token
Session token required for authenticated broker API calls.

## Auth Mode
How login is done (`manual` token vs `auto` flow where supported).

## Stale Instrument Cache
Local symbol/token database is out of date.

## Idempotency Tag
Client-side unique tag used to reduce duplicate order risk.
