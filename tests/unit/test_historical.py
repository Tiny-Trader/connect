"""Unit tests for historical OHLC — transformers and PortfolioMixin.get_historical."""

from __future__ import annotations

from datetime import datetime

from tt_connect.core.timezone import IST
from unittest.mock import AsyncMock, MagicMock

import pytest

from tt_connect.brokers.angelone.transformer import AngelOneTransformer
from tt_connect.brokers.zerodha.adapter import ZerodhaAdapter
from tt_connect.brokers.zerodha.transformer import ZerodhaTransformer
from tt_connect.core.models.enums import CandleInterval
from tt_connect.core.exceptions import AuthenticationError, BrokerError
from tt_connect.core.store.resolver import ResolvedInstrument
from tt_connect.core.models.instruments import Equity, Instrument
from tt_connect.core.models import Candle, GetHistoricalRequest
from tt_connect.core.client._portfolio import PortfolioMixin


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

INSTR    = Equity(exchange="NSE", symbol="RELIANCE")
RESOLVED = ResolvedInstrument(token="2885", broker_symbol="RELIANCE", exchange="NSE")

FROM_DT = datetime(2024, 1, 1, 9, 15, 0, tzinfo=IST)
TO_DT   = datetime(2024, 1, 1, 15, 30, 0, tzinfo=IST)


def _make_client() -> PortfolioMixin:
    class _Fake(PortfolioMixin):
        def _require_connected(self) -> None:
            pass

        async def _resolve(self, instrument: Instrument) -> ResolvedInstrument:
            return RESOLVED

    client: _Fake = object.__new__(_Fake)
    client._adapter = MagicMock()
    return client


# ---------------------------------------------------------------------------
# Zerodha transformer — to_historical_params
# ---------------------------------------------------------------------------


def test_zerodha_to_historical_params_minute1():
    req = GetHistoricalRequest(
        instrument=INSTR, interval=CandleInterval.MINUTE_1,
        from_date=FROM_DT, to_date=TO_DT,
    )
    params = ZerodhaTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
    assert params["interval"] == "minute"
    assert params["from"] == "2024-01-01 09:15:00"
    assert params["to"]   == "2024-01-01 15:30:00"


def test_zerodha_to_historical_params_day():
    req = GetHistoricalRequest(
        instrument=INSTR, interval=CandleInterval.DAY,
        from_date=FROM_DT, to_date=TO_DT,
    )
    params = ZerodhaTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
    assert params["interval"] == "day"


def test_zerodha_to_historical_params_all_intervals():
    """All CandleInterval values must map to a Zerodha string."""
    for ci in CandleInterval:
        req = GetHistoricalRequest(
            instrument=INSTR, interval=ci,
            from_date=FROM_DT, to_date=TO_DT,
        )
        params = ZerodhaTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
        assert "interval" in params
        assert isinstance(params["interval"], str)


def test_zerodha_to_historical_params_oi_included_by_default():
    """include_oi defaults to True — oi=1 should appear in params."""
    req = GetHistoricalRequest(
        instrument=INSTR, interval=CandleInterval.MINUTE_1,
        from_date=FROM_DT, to_date=TO_DT,
    )
    params = ZerodhaTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
    assert params["oi"] == "1"


def test_zerodha_to_historical_params_oi_opt_out():
    """When include_oi=False, the oi param must not be sent."""
    req = GetHistoricalRequest(
        instrument=INSTR, interval=CandleInterval.MINUTE_1,
        from_date=FROM_DT, to_date=TO_DT, include_oi=False,
    )
    params = ZerodhaTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
    assert "oi" not in params


# ---------------------------------------------------------------------------
# Zerodha transformer — to_candles
# ---------------------------------------------------------------------------


def test_zerodha_to_candles_basic():
    rows = [
        ["2024-01-01 09:15:00+0530", 100.0, 105.0, 99.0, 103.0, 500, 0],
        ["2024-01-01 09:20:00+0530", 103.0, 108.0, 102.0, 107.0, 300, 0],
    ]
    candles = ZerodhaTransformer.to_candles(rows, INSTR)
    assert len(candles) == 2
    c = candles[0]
    assert c.instrument is INSTR
    assert c.open  == pytest.approx(100.0)
    assert c.high  == pytest.approx(105.0)
    assert c.low   == pytest.approx(99.0)
    assert c.close == pytest.approx(103.0)
    assert c.volume == 500
    assert c.oi == 0


def test_zerodha_to_candles_without_oi():
    """Rows with only 6 elements (no OI column) should give oi=None."""
    rows = [["2024-01-01 09:15:00+0530", 100.0, 105.0, 99.0, 103.0, 500]]
    candles = ZerodhaTransformer.to_candles(rows, INSTR)
    assert candles[0].oi is None


def test_zerodha_to_candles_empty():
    assert ZerodhaTransformer.to_candles([], INSTR) == []


# ---------------------------------------------------------------------------
# AngelOne transformer — to_historical_params
# ---------------------------------------------------------------------------


def test_angelone_to_historical_params_minute1():
    req = GetHistoricalRequest(
        instrument=INSTR, interval=CandleInterval.MINUTE_1,
        from_date=FROM_DT, to_date=TO_DT,
    )
    params = AngelOneTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
    assert params["interval"]    == "ONE_MINUTE"
    assert params["exchange"]    == "NSE"
    assert params["symboltoken"] == "2885"
    assert params["fromdate"]    == "2024-01-01 09:15"
    assert params["todate"]      == "2024-01-01 15:30"


def test_angelone_to_historical_params_day():
    req = GetHistoricalRequest(
        instrument=INSTR, interval=CandleInterval.DAY,
        from_date=FROM_DT, to_date=TO_DT,
    )
    params = AngelOneTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
    assert params["interval"] == "ONE_DAY"


def test_angelone_to_historical_params_all_intervals():
    for ci in CandleInterval:
        req = GetHistoricalRequest(
            instrument=INSTR, interval=ci,
            from_date=FROM_DT, to_date=TO_DT,
        )
        params = AngelOneTransformer.to_historical_params("2885", "RELIANCE", "NSE", req)
        assert "interval" in params
        assert isinstance(params["interval"], str)


# ---------------------------------------------------------------------------
# AngelOne transformer — to_candles
# ---------------------------------------------------------------------------


def test_angelone_to_candles_basic():
    rows = [
        ["2024-01-01T09:15:00+05:30", 100.0, 105.0, 99.0, 103.0, 500],
        ["2024-01-01T09:20:00+05:30", 103.0, 108.0, 102.0, 107.0, 300],
    ]
    candles = AngelOneTransformer.to_candles(rows, INSTR)
    assert len(candles) == 2
    c = candles[0]
    assert c.instrument is INSTR
    assert c.open  == pytest.approx(100.0)
    assert c.high  == pytest.approx(105.0)
    assert c.close == pytest.approx(103.0)
    assert c.volume == 500
    assert c.oi is None


def test_angelone_to_candles_empty():
    assert AngelOneTransformer.to_candles([], INSTR) == []


# ---------------------------------------------------------------------------
# PortfolioMixin — get_historical
# ---------------------------------------------------------------------------


async def test_get_historical_resolves_and_returns_candles():
    client = _make_client()

    expected_candles = [
        Candle(
            instrument=INSTR,
            timestamp=datetime(2024, 1, 1, 9, 15, tzinfo=IST),
            open=100.0, high=105.0, low=99.0, close=103.0, volume=500,
        )
    ]
    raw_rows = [["2024-01-01T09:15:00+05:30", 100.0, 105.0, 99.0, 103.0, 500]]

    client._adapter.transformer.to_historical_params.return_value = {"interval": "ONE_MINUTE"}
    client._adapter.get_historical = AsyncMock(return_value={"data": raw_rows})
    client._adapter.transformer.to_candles.return_value = expected_candles

    result = await client.get_historical(INSTR, CandleInterval.MINUTE_1, FROM_DT, TO_DT)

    assert result is expected_candles
    client._adapter.get_historical.assert_awaited_once_with(
        RESOLVED.token, {"interval": "ONE_MINUTE"}
    )
    client._adapter.transformer.to_candles.assert_called_once_with(raw_rows, INSTR)


async def test_get_historical_empty_data_returns_empty_list():
    client = _make_client()

    client._adapter.transformer.to_historical_params.return_value = {"interval": "ONE_DAY"}
    client._adapter.get_historical = AsyncMock(return_value={"data": []})
    client._adapter.transformer.to_candles.return_value = []

    result = await client.get_historical(INSTR, CandleInterval.DAY, FROM_DT, TO_DT)

    assert result == []


@pytest.mark.asyncio
async def test_zerodha_adapter_get_historical_raises_on_malformed_payload() -> None:
    adapter = ZerodhaAdapter({"api_key": "k", "access_token": "t"})
    adapter._request = AsyncMock(return_value={"status": "success", "data": {}})  # type: ignore[method-assign]

    with pytest.raises(BrokerError, match="data.candles"):
        await adapter.get_historical("2885", {"interval": "day", "from": "x", "to": "y"})


def test_zerodha_create_ws_client_raises_when_access_token_missing() -> None:
    adapter = ZerodhaAdapter({"api_key": "k", "access_token": "t"})
    adapter.auth._session = None

    with pytest.raises(AuthenticationError, match="access_token"):
        adapter.create_ws_client()


def test_zerodha_create_ws_client_raises_when_api_key_missing() -> None:
    adapter = ZerodhaAdapter({"api_key": "k", "access_token": "t"})
    adapter._config["api_key"] = ""

    with pytest.raises(AuthenticationError, match="api_key"):
        adapter.create_ws_client()
