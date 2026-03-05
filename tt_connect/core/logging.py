"""Structured JSON logging utilities for tt-connect."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Mapping
from typing import Literal

_STDLIB_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message", "asctime",
})


class TTConnectJsonFormatter(logging.Formatter):
    """Emit one JSON line per log record with stable fields and merged extras."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        utc = timezone.utc
        ts = datetime.fromtimestamp(record.created, tz=utc).isoformat(timespec="milliseconds")

        payload: dict[str, object] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }

        # Merge caller-supplied extra fields
        for key, val in record.__dict__.items():
            if key not in _STDLIB_ATTRS and not key.startswith("_"):
                payload[key] = val

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


_HANDLER_MARKER = "_tt_connect_handler"
_STARTUP_LOGGED = False
_UPGRADE_HINTS_EMITTED: set[str] = set()

_DEPRECATED_CONFIG_KEYS: dict[str, str] = {
    "apiKey": "api_key",
    "accessToken": "access_token",
    "clientId": "client_id",
    "totpSecret": "totp_secret",
    "authMode": "auth_mode",
    "cacheSession": "cache_session",
    "onStale": "on_stale",
}


def setup_logging(level: str = "INFO", fmt: Literal["json", "text"] = "json") -> None:
    """Configure the tt_connect package logger to emit to stderr.

    Idempotent — repeated calls update the formatter and level without
    stacking duplicate handlers. Call once at application startup.
    By default the tt_connect logger ships with a NullHandler (silent).
    """
    pkg_logger = logging.getLogger("tt_connect")
    pkg_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = (
        TTConnectJsonFormatter()
        if fmt == "json"
        else logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    )

    # If our handler is already attached, just swap the formatter.
    for h in pkg_logger.handlers:
        if getattr(h, _HANDLER_MARKER, False):
            h.setFormatter(formatter)
            return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    setattr(handler, _HANDLER_MARKER, True)
    pkg_logger.addHandler(handler)


def _pkg_version() -> str:
    try:
        return version("tt-connect")
    except PackageNotFoundError:
        return "unknown"


def log_package_startup(broker: str, config: Mapping[str, object]) -> None:
    """Emit a one-time startup event for process-level observability."""
    global _STARTUP_LOGGED
    if _STARTUP_LOGGED:
        return

    logger = logging.getLogger("tt_connect")
    logger.info(
        "tt-connect startup",
        extra={
            "event": "package.startup",
            "tt_connect_version": _pkg_version(),
            "broker": broker,
            "auth_mode": str(config.get("auth_mode", "manual")),
            "on_stale": str(config.get("on_stale", "fail")),
            "cache_session": bool(config.get("cache_session", False)),
        },
    )
    _STARTUP_LOGGED = True


def log_upgrade_notice(code: str, hint: str) -> None:
    """Emit an upgrade/migration hint once per process for a unique code."""
    if code in _UPGRADE_HINTS_EMITTED:
        return
    logging.getLogger("tt_connect").info(
        "upgrade notice",
        extra={"event": "upgrade.notice", "code": code, "hint": hint},
    )
    _UPGRADE_HINTS_EMITTED.add(code)


def log_deprecated_config_keys(config: Mapping[str, object]) -> None:
    """Log migration hints for deprecated config key names once per key."""
    for old_key, new_key in _DEPRECATED_CONFIG_KEYS.items():
        if old_key in config:
            log_upgrade_notice(
                code=f"deprecated_config_key:{old_key}",
                hint=f"Use '{new_key}' instead of '{old_key}'.",
            )


def _reset_upgrade_log_state_for_tests() -> None:
    """Reset one-time logging guards. Test-only helper."""
    global _STARTUP_LOGGED
    _STARTUP_LOGGED = False
    _UPGRADE_HINTS_EMITTED.clear()
