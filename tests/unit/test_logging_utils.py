"""Tests for tt_connect.logging_utils — TTConnectJsonFormatter and setup_logging."""

from __future__ import annotations

import json
import logging

from tt_connect.logging_utils import TTConnectJsonFormatter, setup_logging


def _make_record(
    msg: str = "hello",
    level: int = logging.INFO,
    name: str = "tt_connect.test",
    extra: dict | None = None,
    exc_info: bool = False,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=0,
        msg=msg,
        args=(),
        exc_info=(ValueError, ValueError("oops"), None) if exc_info else None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


class TestTTConnectJsonFormatter:
    def setup_method(self) -> None:
        self.fmt = TTConnectJsonFormatter()

    def test_json_formatter_emits_valid_json(self) -> None:
        record = _make_record()
        output = self.fmt.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_formatter_standard_fields(self) -> None:
        record = _make_record(msg="test message", level=logging.WARNING, name="tt_connect.foo")
        output = self.fmt.format(record)
        parsed = json.loads(output)
        assert "ts" in parsed
        assert parsed["level"] == "WARNING"
        assert parsed["logger"] == "tt_connect.foo"
        assert parsed["message"] == "test message"

    def test_json_formatter_merges_extra_fields(self) -> None:
        record = _make_record(extra={"event": "auth.login", "broker": "zerodha"})
        output = self.fmt.format(record)
        parsed = json.loads(output)
        assert parsed["event"] == "auth.login"
        assert parsed["broker"] == "zerodha"

    def test_json_formatter_includes_exception(self) -> None:
        record = _make_record(exc_info=True)
        output = self.fmt.format(record)
        parsed = json.loads(output)
        assert "exc" in parsed
        assert "ValueError" in parsed["exc"]

    def test_json_formatter_non_serialisable_uses_str(self) -> None:
        obj = object()
        record = _make_record(extra={"obj": obj})
        # Must not raise
        output = self.fmt.format(record)
        parsed = json.loads(output)
        assert "obj" in parsed

    def test_setup_logging_adds_handler(self) -> None:
        pkg_logger = logging.getLogger("tt_connect")
        # Remove any handlers from a previous test run
        pkg_logger.handlers.clear()

        setup_logging(level="DEBUG", fmt="json")

        assert len(pkg_logger.handlers) >= 1
        handler = pkg_logger.handlers[-1]
        assert isinstance(handler.formatter, TTConnectJsonFormatter)
