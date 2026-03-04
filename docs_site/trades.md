# Trades

## What is a trade
A trade is an executed fill of an order.

## Important behavior
- one order can create many trades (partial fills)
- avg price is computed from fills
- trade timestamps are broker-provided

## Usage
- use trades for execution reports
- reconcile trades with final order status
