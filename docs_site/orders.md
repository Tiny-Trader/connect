# Orders

## Core actions
- place order
- modify order
- cancel order
- list orders

## Order flow
`PENDING -> OPEN -> COMPLETE` or `CANCELLED` or `REJECTED`

## Place order checklist
- valid instrument
- side (BUY/SELL)
- qty > 0
- valid order type/product type
- price/trigger when needed

## Good patterns
- save returned order id
- poll order status after placement
- handle rejection reason and fallback
