# Order Rejected

## Common symptoms
- order status becomes `REJECTED`
- `BrokerError`, `InvalidOrderError`, or `InsufficientFundsError`

## Fast checks
1. Check available funds before placing order.
2. Verify product type/order type is supported for broker+segment.
3. Verify required fields for order type (price/trigger).
4. Read latest order book entry for broker message.

## Debug pattern
```python
orders = broker.get_orders()
for o in orders[:10]:
    print(o.id, o.status, o.order_type, o.product, o.qty)
```

## Safe recovery
- Do not blindly retry same payload.
- Fix root cause first (funds/params/capability).
- Re-submit only after checks pass.

## Related
- [Orders](../orders.md)
- [Errors & Retries](../errors-and-retries.md)
- [Broker capabilities](../reference/capabilities.md)
