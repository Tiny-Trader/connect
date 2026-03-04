# Realtime (WebSocket)

## Core flow
- connect
- subscribe instruments
- receive ticks in callback
- unsubscribe
- close client cleanly

## Reliability behavior
- reconnect is automatic
- subscriptions should recover after reconnect

## Callback best practices
- keep callback non-blocking
- push tick to queue/worker
- handle parsing/business errors inside callback
