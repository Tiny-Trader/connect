"""Unit tests for InstrumentResolver.reverse_resolve."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from tt_connect.core.store.resolver import InstrumentResolver
from tt_connect.core.models.instruments import Equity, Future, Index, Option
from tt_connect.core.models.enums import Exchange, OptionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_resolver() -> InstrumentResolver:
    conn = MagicMock()
    return InstrumentResolver(conn, broker_id="zerodha")


def _mock_cursor(row):
    """Return a mock async context manager that yields one fetchone result."""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=row)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=cursor)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# reverse_resolve — subtypes
# ---------------------------------------------------------------------------


async def test_reverse_resolve_equity():
    resolver = _make_resolver()
    # (exchange, symbol, segment, fut_exch, fut_sym, fut_expiry,
    #  opt_exch, opt_sym, opt_expiry, strike, option_type)
    row = ("NSE", "RELIANCE", "EQ", None, None, None, None, None, None, None, None)
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(row))

    result = await resolver.reverse_resolve("738561")

    assert isinstance(result, Equity)
    assert result.exchange == Exchange.NSE
    assert result.symbol == "RELIANCE"


async def test_reverse_resolve_index():
    resolver = _make_resolver()
    row = ("NSE", "NIFTY", "INDICES", None, None, None, None, None, None, None, None)
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(row))

    result = await resolver.reverse_resolve("256265")

    assert isinstance(result, Index)
    assert result.exchange == Exchange.NSE
    assert result.symbol == "NIFTY"


async def test_reverse_resolve_future():
    resolver = _make_resolver()
    row = (
        "NFO", "NIFTY", "FUT",
        "NSE", "NIFTY", "2026-03-27",
        None, None, None, None, None,
    )
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(row))

    result = await resolver.reverse_resolve("some_token")

    assert isinstance(result, Future)
    assert result.exchange == Exchange.NSE
    assert result.symbol == "NIFTY"
    assert str(result.expiry) == "2026-03-27"


async def test_reverse_resolve_option():
    resolver = _make_resolver()
    row = (
        "NFO", "NIFTY", "OPT",
        None, None, None,
        "NSE", "NIFTY", "2026-03-27", 22000.0, "CE",
    )
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(row))

    result = await resolver.reverse_resolve("some_token")

    assert isinstance(result, Option)
    assert result.exchange == Exchange.NSE
    assert result.symbol == "NIFTY"
    assert result.strike == 22000.0
    assert result.option_type == OptionType.CE


async def test_reverse_resolve_not_found():
    resolver = _make_resolver()
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(None))

    result = await resolver.reverse_resolve("nonexistent")

    assert result is None


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


async def test_reverse_resolve_cached_result_skips_db():
    resolver = _make_resolver()
    row = ("NSE", "RELIANCE", "EQ", None, None, None, None, None, None, None, None)
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(row))

    first = await resolver.reverse_resolve("738561")
    second = await resolver.reverse_resolve("738561")

    assert first is second
    # DB was only hit once
    assert resolver._conn.execute.call_count == 1


async def test_reverse_resolve_caches_none_result():
    resolver = _make_resolver()
    resolver._conn.execute = MagicMock(return_value=_mock_cursor(None))

    first = await resolver.reverse_resolve("bad_token")
    second = await resolver.reverse_resolve("bad_token")

    assert first is None
    assert second is None
    assert resolver._conn.execute.call_count == 1
