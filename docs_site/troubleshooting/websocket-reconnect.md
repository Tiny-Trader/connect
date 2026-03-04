# WebSocket Disconnect/Reconnect

## Common symptoms
- ticks stop suddenly
- short data gaps during reconnect
- callback exceptions hide useful errors

## Expected behavior
- websocket reconnect is automatic
- existing subscriptions are restored after reconnect

## Fast checks
1. Keep callback non-blocking.
2. Catch and log callback exceptions.
3. Track last tick timestamp per symbol.

## Safe callback pattern
```python
last_ts = {}

async def on_tick(tick):
    key = f"{tick.instrument.exchange}:{tick.instrument.symbol}"
    last_ts[key] = tick.timestamp
    # enqueue to worker instead of heavy logic here
```

## When to alert
- no tick for monitored symbol beyond your threshold
- repeated reconnect loops with no stable stream

## Related
- [Realtime (WebSocket)](../realtime-websocket.md)
- [Recipe: Recover from reconnect](../recipes/recover-from-reconnect.md)
- [Broker operation notes](../reference/operation-notes.md)
