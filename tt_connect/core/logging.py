"""Structured JSON logging utilities for tt-connect."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
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
