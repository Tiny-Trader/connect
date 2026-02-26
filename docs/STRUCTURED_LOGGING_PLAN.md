# Structured Logging Plan

This document outlines options, design choices, rollout phases, and acceptance criteria for structured logging in `tt-connect`.

## Decisions (2026-02-27)

1. Option A (stdlib `logging` + custom JSON formatter) is the chosen implementation.
2. Capture all relevant events by default in implementation; sanitize/redact sensitive fields before emission.
3. Let users control effective verbosity using logger level configuration.
4. Introduce a typed logging config model integrated with existing global config models.
5. For correlation, generate `request_id` internally and optionally support a caller-provided `correlation_id` field later.

## 1. Goals

1. Make logs machine-parseable and queryable (JSON records).
2. Log every outbound broker request lifecycle with timing and outcomes.
3. Preserve safety by default (no secrets, no PII leaks).
4. Keep it lightweight for library users (stdlib-first, opt-in verbosity).
5. Support correlation across retries, lifecycle operations, and WebSocket sessions.

## 2. What To Log

1. `request.start`: before HTTP call.
2. `request.end`: on success with latency and response metadata.
3. `request.error`: broker/HTTP/timeout/parse failure with typed error info.
4. `auth.login`, `auth.refresh`, `auth.cache_hit`, `auth.cache_miss`.
5. `instruments.refresh.start`, `instruments.refresh.end`, `instruments.refresh.fail`.
6. `resolver.cache_hit`, `resolver.cache_miss`.
7. `ws.connect`, `ws.reconnect`, `ws.subscribe`, `ws.unsubscribe`, `ws.error`.
8. `client.state_change` for `CREATED -> CONNECTED -> CLOSED`.

## 3. Canonical Log Schema

1. `ts` ISO8601 UTC.
2. `level` (`DEBUG|INFO|WARNING|ERROR`).
3. `event` short stable event name.
4. `component` (`adapter.base`, `auth.angelone`, etc.).
5. `broker` (`zerodha|angelone`).
6. `request_id` UUID per outbound HTTP attempt.
7. `operation_id` UUID across retries for the same logical operation.
8. `method`, `path`, `status_code`, `latency_ms`.
9. `attempt`, `max_retries`, `retryable`.
10. `error_type`, `broker_code`, `message` (sanitized).
11. `extra` free-form dict for endpoint-specific fields.

## 4. Sensitive Data Policy

1. Never log tokens, secrets, headers with auth, passwords, TOTP, refresh tokens.
2. Redact known keys recursively: `access_token`, `refresh_token`, `Authorization`, `pin`, `totp_secret`, `api_key`.
3. Truncate large payloads (`max_payload_bytes`, default 2KB).
4. Hash optional user identifiers when needed (if account-level diagnostics are required).

## 5. Options and Tradeoffs

### Option A: stdlib `logging` + custom JSON formatter (Recommended)

1. Pros: zero heavy dependency, user-friendly in library context, easy adoption.
2. Pros: aligns with project TODO to use Python stdlib logging.
3. Cons: less ergonomic context binding than `structlog`.

### Option B: `structlog` on top of stdlib

1. Pros: strong structured logging ergonomics, context propagation, processors.
2. Pros: easy to add human-readable dev renderer.
3. Cons: new dependency and migration overhead for contributors/users.

### Option C: OpenTelemetry logs/spans integration

1. Pros: rich observability (logs + traces + metrics correlation).
2. Pros: production-grade backend compatibility.
3. Cons: highest complexity, overkill for initial rollout.

### Option D: `loguru`

1. Pros: simple API.
2. Cons: non-stdlib, less suitable for reusable libraries, global logger behavior can conflict with host app.

## 6. Recommendation

1. Implement Option A now (locked decision).
2. Keep interfaces compatible with future Option B/C (schema-first design).
3. Add `structlog` only if logs become hard to manage with stdlib.

## 7. Proposed Configuration API

Add config knobs in [`tt_connect/config.py`](../tt_connect/config.py):

1. `log_enabled: bool = True`
2. `log_level: str = "INFO"`
3. `log_format: Literal["json", "text"] = "json"`
4. `log_sample_rate: float = 1.0`
5. `log_include_payloads: bool = True`
6. `log_redact_sensitive: bool = True`
7. `log_max_payload_bytes: int = 2048`

Define these as a typed model (for example `LoggingConfig`) and include it in broker/global config models.
User-selected `log_level` determines effective output volume.

## 8. Implementation Plan by File

1. Add logging utilities:
   - [`tt_connect/logging_utils.py`](../tt_connect/logging_utils.py)
   - JSON formatter, redaction helpers, context binding, sampling helper.
2. Instrument HTTP adapter:
   - [`tt_connect/adapters/base.py`](../tt_connect/adapters/base.py)
   - Emit `request.start/end/error` in `_request`.
3. Instrument auth flows:
   - [`tt_connect/auth/base.py`](../tt_connect/auth/base.py)
   - [`tt_connect/adapters/angelone/auth.py`](../tt_connect/adapters/angelone/auth.py)
   - [`tt_connect/adapters/zerodha/auth.py`](../tt_connect/adapters/zerodha/auth.py)
4. Instrument lifecycle and resolver:
   - [`tt_connect/lifecycle.py`](../tt_connect/lifecycle.py)
   - [`tt_connect/instrument_manager/manager.py`](../tt_connect/instrument_manager/manager.py)
   - [`tt_connect/instrument_manager/resolver.py`](../tt_connect/instrument_manager/resolver.py)
5. Instrument WebSocket clients:
   - [`tt_connect/ws/angelone.py`](../tt_connect/ws/angelone.py)
   - [`tt_connect/ws/zerodha.py`](../tt_connect/ws/zerodha.py)

## 9. Rollout Phases

1. Phase 1: HTTP request lifecycle logs in `adapters/base.py`.
2. Phase 2: auth + lifecycle + instrument refresh logs.
3. Phase 3: WebSocket logs with reconnect and subscription context.
4. Phase 4: docs, examples, and production guidance.
5. Phase 5: optional OpenTelemetry hooks if needed.

## 10. Acceptance Criteria

1. Every outbound REST request has a start and terminal event.
2. Latency and retry attempt data are always present.
3. No secrets appear in logs (unit test enforced).
4. JSON logs validate as one JSON object per line.
5. All non-sensitive event fields are captured; filtering is controlled by logger level.

## 11. Testing Plan

1. Unit tests for formatter output shape.
2. Unit tests for redaction (recursive objects, headers, nested keys).
3. Unit tests for sampling behavior.
4. Integration tests asserting emitted events around mocked HTTP retries/timeouts.
5. Regression tests to ensure auth tokens are never logged.

## 12. Example Log Record

```json
{
  "ts":"2026-02-27T05:11:22.901Z",
  "level":"INFO",
  "event":"request.end",
  "component":"adapter.base",
  "broker":"zerodha",
  "operation_id":"4d3c8f6e-5d9d-4e78-b0f5-7f1a8e15b4d1",
  "request_id":"8ea0bb2b-c8fd-467a-9f7b-57f676f3fa31",
  "method":"GET",
  "path":"/user/profile",
  "status_code":200,
  "latency_ms":83,
  "attempt":1,
  "max_retries":3
}
```

## 13. Open Decisions To Finalize Before Coding

1. Should sampling apply to all logs or only high-volume events?
2. Should caller-provided `correlation_id` be added in Phase 1 or deferred to a later phase?
