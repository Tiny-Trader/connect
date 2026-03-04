# Positions

## What is a position
Current net open quantity for an instrument.

## Key points
- positive qty: long
- negative qty: short
- zero qty: closed/flat

## Common actions
- read open positions
- compute live pnl using ltp
- close single or all positions

## Caution
close-all sends market actions; always verify product/segment limits.

## See also
- [Client methods (`get_positions`, `close_all_positions`)](reference/clients.md)
- [Models (`Position`)](reference/models.md)
- [Enums (`ProductType`, `Side`)](reference/enums.md)
- [Recipe: Close all open positions](recipes/close-all-open-positions.md)
