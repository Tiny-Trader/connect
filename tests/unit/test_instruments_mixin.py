"""Unit tests for InstrumentsMixin (get_futures, get_options, get_expiries)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from tt_connect.core.models.instruments import Equity, Future, Option
from tt_connect.core.client._instruments import InstrumentsMixin
from tt_connect.core.store.resolver import ResolvedInstrument


SBIN = Equity(exchange="NSE", symbol="SBIN")

EXP1 = date(2025, 3, 27)
EXP2 = date(2025, 4, 24)

FUTURES = [
    Future(exchange="NSE", symbol="SBIN", expiry=EXP1),
    Future(exchange="NSE", symbol="SBIN", expiry=EXP2),
]

OPTIONS = [
    Option(exchange="NSE", symbol="SBIN", expiry=EXP1, strike=700.0, option_type="CE"),
    Option(exchange="NSE", symbol="SBIN", expiry=EXP1, strike=700.0, option_type="PE"),
    Option(exchange="NSE", symbol="SBIN", expiry=EXP1, strike=720.0, option_type="CE"),
    Option(exchange="NSE", symbol="SBIN", expiry=EXP1, strike=720.0, option_type="PE"),
]


def _make_client() -> InstrumentsMixin:
    class _Fake(InstrumentsMixin):
        def _require_connected(self) -> None:
            pass

        async def _resolve(self, instrument):  # type: ignore[override]
            return ResolvedInstrument(token="1", broker_symbol="SBIN", exchange="NSE")

    client: _Fake = object.__new__(_Fake)
    client._instrument_manager = MagicMock()
    return client


# ---------------------------------------------------------------------------
# get_futures
# ---------------------------------------------------------------------------

async def test_get_futures_delegates_to_manager():
    client = _make_client()
    client._instrument_manager.get_futures = AsyncMock(return_value=FUTURES)

    result = await client.get_futures(SBIN)

    assert result == FUTURES
    client._instrument_manager.get_futures.assert_awaited_once_with(SBIN)


async def test_get_futures_returns_empty_list():
    client = _make_client()
    client._instrument_manager.get_futures = AsyncMock(return_value=[])

    result = await client.get_futures(SBIN)

    assert result == []


# ---------------------------------------------------------------------------
# get_options
# ---------------------------------------------------------------------------

async def test_get_options_no_expiry_filter():
    client = _make_client()
    client._instrument_manager.get_options = AsyncMock(return_value=OPTIONS)

    result = await client.get_options(SBIN)

    assert result == OPTIONS
    client._instrument_manager.get_options.assert_awaited_once_with(SBIN, None)


async def test_get_options_with_expiry_filter():
    client = _make_client()
    filtered = [o for o in OPTIONS if o.expiry == EXP1]
    client._instrument_manager.get_options = AsyncMock(return_value=filtered)

    result = await client.get_options(SBIN, expiry=EXP1)

    assert all(o.expiry == EXP1 for o in result)
    client._instrument_manager.get_options.assert_awaited_once_with(SBIN, EXP1)


# ---------------------------------------------------------------------------
# get_expiries
# ---------------------------------------------------------------------------

async def test_get_expiries_returns_sorted_dates():
    client = _make_client()
    client._instrument_manager.get_expiries = AsyncMock(return_value=[EXP1, EXP2])

    result = await client.get_expiries(SBIN)

    assert result == [EXP1, EXP2]
    client._instrument_manager.get_expiries.assert_awaited_once_with(SBIN)


async def test_get_expiries_empty_when_no_derivatives():
    client = _make_client()
    client._instrument_manager.get_expiries = AsyncMock(return_value=[])

    result = await client.get_expiries(Equity(exchange="NSE", symbol="SMALLCAP"))

    assert result == []


# ---------------------------------------------------------------------------
# search_instruments
# ---------------------------------------------------------------------------

async def test_search_instruments_delegates_to_manager():
    client = _make_client()
    expected = [Equity(exchange="NSE", symbol="SBIN")]
    client._instrument_manager.search_instruments = AsyncMock(return_value=expected)

    result = await client.search_instruments("SBI")

    assert result == expected
    client._instrument_manager.search_instruments.assert_awaited_once_with("SBI", None)


async def test_search_instruments_with_exchange_filter():
    client = _make_client()
    expected = [Equity(exchange="NSE", symbol="RELIANCE")]
    client._instrument_manager.search_instruments = AsyncMock(return_value=expected)

    result = await client.search_instruments("REL", exchange="NSE")

    assert result == expected
    client._instrument_manager.search_instruments.assert_awaited_once_with("REL", "NSE")

