"""Unit tests for Zerodha market quotes — transformer and PortfolioMixin."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tt_connect.brokers.angelone.transformer import AngelOneTransformer
from tt_connect.brokers.zerodha.transformer import ZerodhaTransformer
from tt_connect.core.exceptions import UnsupportedFeatureError
from tt_connect.core.store.resolver import ResolvedInstrument
from tt_connect.core.models.instruments import Equity
from tt_connect.core.models import Tick
from tt_connect.core.client._portfolio import PortfolioMixin

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

INSTR    = Equity(exchange="NSE", symbol="RELIANCE")
INSTR2   = Equity(exchange="NSE", symbol="SBIN")
RESOLVED = ResolvedInstrument(token="738561", broker_symbol="RELIANCE", exchange="NSE")

_FIXTURE = json.loads(
    (Path(__file__).parent.parent / "fixtures/responses/zerodha/quotes.json").read_text()
)
_RAW_RELIANCE = _FIXTURE["data"]["NSE:RELIANCE"]
_RAW_SBIN     = _FIXTURE["data"]["NSE:SBIN"]


def _make_client(resolved: ResolvedInstrument = RESOLVED) -> PortfolioMixin:
    class _Fake(PortfolioMixin):
        def _require_connected(self) -> None:
            pass

        async def _resolve(self, instrument):  # type: ignore[override]
            return resolved

    client: _Fake = object.__new__(_Fake)
    client._adapter = MagicMock()
    return client


# ---------------------------------------------------------------------------
# ZerodhaTransformer.to_quote
# ---------------------------------------------------------------------------


def test_to_quote_basic():
    tick = ZerodhaTransformer.to_quote(_RAW_RELIANCE, INSTR)
    assert isinstance(tick, Tick)
    assert tick.instrument is INSTR
    assert tick.ltp == pytest.approx(2450.0)
    assert tick.volume == 3542100


def test_to_quote_timestamp_parsed():
    tick = ZerodhaTransformer.to_quote(_RAW_RELIANCE, INSTR)
    assert isinstance(tick.timestamp, datetime)
    assert tick.timestamp == datetime(2024, 1, 15, 15, 30, 0)


def test_to_quote_zero_oi_becomes_none():
    """Zerodha returns oi=0 for equities — we normalise 0 to None."""
    tick = ZerodhaTransformer.to_quote({**_RAW_RELIANCE, "oi": 0}, INSTR)
    assert tick.oi is None


def test_to_quote_nonzero_oi_preserved():
    tick = ZerodhaTransformer.to_quote({**_RAW_RELIANCE, "oi": 123456}, INSTR)
    assert tick.oi == 123456


def test_to_quote_missing_timestamp_returns_none():
    raw = {**_RAW_RELIANCE, "timestamp": None, "last_trade_time": None}
    tick = ZerodhaTransformer.to_quote(raw, INSTR)
    assert tick.timestamp is None


def test_to_quote_falls_back_to_last_trade_time():
    raw = {**_RAW_RELIANCE, "timestamp": None, "last_trade_time": "2024-01-15 15:29:58"}
    tick = ZerodhaTransformer.to_quote(raw, INSTR)
    assert isinstance(tick.timestamp, datetime)


def test_to_quote_bid_ask_extracted_from_depth():
    tick = ZerodhaTransformer.to_quote(_RAW_RELIANCE, INSTR)
    assert tick.bid == pytest.approx(2449.5)
    assert tick.ask == pytest.approx(2450.5)


def test_to_quote_zero_bid_ask_becomes_none():
    """Depth prices of 0 (empty book) should be normalised to None."""
    raw = {
        **_RAW_RELIANCE,
        "depth": {
            "buy":  [{"price": 0, "quantity": 0, "orders": 0}],
            "sell": [{"price": 0, "quantity": 0, "orders": 0}],
        },
    }
    tick = ZerodhaTransformer.to_quote(raw, INSTR)
    assert tick.bid is None
    assert tick.ask is None


def test_to_quote_no_depth_field():
    """Response without depth key (e.g. /quote/ltp) should give None bid/ask."""
    raw = {k: v for k, v in _RAW_RELIANCE.items() if k != "depth"}
    tick = ZerodhaTransformer.to_quote(raw, INSTR)
    assert tick.bid is None
    assert tick.ask is None


# ---------------------------------------------------------------------------
# AngelOneTransformer.to_quote — UnsupportedFeatureError
# ---------------------------------------------------------------------------


def test_angelone_to_quote_raises_unsupported():
    with pytest.raises(UnsupportedFeatureError):
        AngelOneTransformer.to_quote({}, INSTR)


# ---------------------------------------------------------------------------
# PortfolioMixin.get_quotes
# ---------------------------------------------------------------------------


async def test_get_quotes_single_instrument():
    client = _make_client()
    expected = Tick(instrument=INSTR, ltp=2450.0, volume=3542100)
    client._adapter.get_quotes = AsyncMock(
        return_value={"data": {"NSE:RELIANCE": _RAW_RELIANCE}}
    )
    client._adapter.transformer.to_quote.return_value = expected

    result = await client.get_quotes([INSTR])

    assert result == [expected]
    client._adapter.get_quotes.assert_awaited_once_with(["NSE:RELIANCE"])
    client._adapter.transformer.to_quote.assert_called_once_with(_RAW_RELIANCE, INSTR)


async def test_get_quotes_multiple_instruments():
    resolved2 = ResolvedInstrument(token="779521", broker_symbol="SBIN", exchange="NSE")

    call_count = 0

    class _Fake(PortfolioMixin):
        def _require_connected(self) -> None:
            pass

        async def _resolve(self, instrument):  # type: ignore[override]
            nonlocal call_count
            call_count += 1
            return RESOLVED if instrument.symbol == "RELIANCE" else resolved2

    client: _Fake = object.__new__(_Fake)
    client._adapter = MagicMock()
    client._adapter.get_quotes = AsyncMock(
        return_value={"data": {"NSE:RELIANCE": _RAW_RELIANCE, "NSE:SBIN": _RAW_SBIN}}
    )
    client._adapter.transformer.to_quote.side_effect = lambda raw, inst: Tick(
        instrument=inst, ltp=float(raw["last_price"])
    )

    result = await client.get_quotes([INSTR, INSTR2])

    assert len(result) == 2
    assert client._adapter.get_quotes.await_args[0][0] == ["NSE:RELIANCE", "NSE:SBIN"]


async def test_get_quotes_missing_key_silently_omitted():
    """If the broker omits a key from the response, that instrument is skipped."""
    client = _make_client()
    client._adapter.get_quotes = AsyncMock(return_value={"data": {}})
    client._adapter.transformer.to_quote.return_value = Tick(instrument=INSTR, ltp=0.0)

    result = await client.get_quotes([INSTR])

    assert result == []
    client._adapter.transformer.to_quote.assert_not_called()
