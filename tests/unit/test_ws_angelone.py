"""Unit tests for the AngelOne SmartStream binary parser and subscription management."""

from __future__ import annotations

import json
import struct
from tt_connect.core.timezone import IST
from unittest.mock import MagicMock, patch

import pytest

from tt_connect.core.models.instruments import Equity
from tt_connect.brokers.angelone.ws import AngelOneWebSocket


# ---------------------------------------------------------------------------
# Helpers — binary packet builders
# ---------------------------------------------------------------------------

TOKEN_STR = "3045"
INSTR     = Equity(exchange="NSE", symbol="SBIN")


def _ao_ltp_packet(
    token: str,
    ltp_paise: int,
    mode: int = 1,
    exchange_type: int = 1,
    ts_ms: int = 0,
) -> bytes:
    """Build a 51-byte LTP-mode AngelOne binary packet (little-endian)."""
    buf = bytearray(51)
    buf[0] = mode
    buf[1] = exchange_type
    tok = token.encode("ascii")[:25]
    buf[2:2 + len(tok)] = tok
    struct.pack_into("<q", buf, 35, ts_ms)
    struct.pack_into("<q", buf, 43, ltp_paise)
    return bytes(buf)


def _ao_quote_packet(
    token: str,
    ltp_paise: int,
    volume: int = 0,
    mode: int = 2,
) -> bytes:
    """Build a 123-byte QUOTE-mode AngelOne binary packet."""
    buf = bytearray(123)
    buf[0] = mode
    tok = token.encode("ascii")[:25]
    buf[2:2 + len(tok)] = tok
    struct.pack_into("<q", buf, 43, ltp_paise)
    struct.pack_into("<q", buf, 67, volume)
    return bytes(buf)


def _ao_snap_quote_packet(
    token: str,
    ltp_paise: int,
    oi: int = 0,
    bid_paise: int = 0,
    ask_paise: int = 0,
) -> bytes:
    """Build a 347-byte SNAP_QUOTE-mode AngelOne binary packet."""
    buf = bytearray(347)
    buf[0] = 3  # SNAP_QUOTE
    tok = token.encode("ascii")[:25]
    buf[2:2 + len(tok)] = tok
    struct.pack_into("<q", buf, 43, ltp_paise)
    struct.pack_into("<q", buf, 131, oi)

    # best5 block starts at byte 147; each entry is 20 bytes: flag(H) qty(q) price(q) orders(H)
    BS = 147
    if bid_paise > 0:
        struct.pack_into("<H", buf, BS + 0,  0)          # flag=0 (buy)
        struct.pack_into("<q", buf, BS + 2,  100)         # qty
        struct.pack_into("<q", buf, BS + 10, bid_paise)   # price
        struct.pack_into("<H", buf, BS + 18, 1)           # orders
    if ask_paise > 0:
        struct.pack_into("<H", buf, BS + 20, 1)           # flag=1 (sell)
        struct.pack_into("<q", buf, BS + 22, 100)         # qty
        struct.pack_into("<q", buf, BS + 30, ask_paise)   # price
        struct.pack_into("<H", buf, BS + 38, 1)           # orders

    return bytes(buf)


def _ws_with_token(token: str, instrument: Equity) -> AngelOneWebSocket:
    """Return an AngelOneWebSocket pre-seeded with a token→instrument mapping."""
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    ws._token_map[token] = instrument
    ws._token_exchange_type[token] = 1
    return ws


# ---------------------------------------------------------------------------
# Tests — _parse_binary (LTP mode)
# ---------------------------------------------------------------------------


def test_ltp_packet_parsed() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    data = _ao_ltp_packet(TOKEN_STR, ltp_paise=49500_00)  # ₹49500.00

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.ltp == pytest.approx(49500.0)
    assert tick.instrument is INSTR
    assert tick.volume is None
    assert tick.oi is None
    assert tick.bid is None
    assert tick.ask is None


def test_ltp_timestamp_zero_gives_none() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    data = _ao_ltp_packet(TOKEN_STR, ltp_paise=100_00, ts_ms=0)

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.timestamp is None


def test_ltp_timestamp_nonzero_parsed() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    ts_ms = 1700000000_000  # epoch ms
    data = _ao_ltp_packet(TOKEN_STR, ltp_paise=100_00, ts_ms=ts_ms)

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.timestamp is not None
    assert tick.timestamp.tzinfo == IST


def test_packet_too_short_returns_none() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    assert ws._parse_binary(b"\x01\x02") is None


def test_unknown_token_returns_none() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)   # empty token map
    data = _ao_ltp_packet(TOKEN_STR, ltp_paise=100_00)

    assert ws._parse_binary(data) is None


def test_token_with_null_padding_parsed() -> None:
    """Token bytes may be null-padded; ensure stripping works."""
    ws = _ws_with_token(TOKEN_STR, INSTR)
    # Build with null-padded token manually
    buf = bytearray(51)
    buf[0] = 1
    buf[2:2 + len(TOKEN_STR)] = TOKEN_STR.encode("ascii")
    # remaining bytes 2+len:27 stay 0x00 (null padding)
    struct.pack_into("<q", buf, 43, 250_00)
    data = bytes(buf)

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.ltp == pytest.approx(250.0)


# ---------------------------------------------------------------------------
# Tests — _parse_binary (QUOTE mode)
# ---------------------------------------------------------------------------


def test_quote_packet_includes_volume() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    data = _ao_quote_packet(TOKEN_STR, ltp_paise=100_00, volume=98765, mode=2)

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.ltp == pytest.approx(100.0)
    assert tick.volume == 98765
    assert tick.oi is None


def test_ltp_mode_in_larger_packet_skips_volume() -> None:
    """Mode=1 in a 123-byte packet should NOT populate volume."""
    ws = _ws_with_token(TOKEN_STR, INSTR)
    data = _ao_quote_packet(TOKEN_STR, ltp_paise=100_00, volume=12345, mode=1)

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.volume is None


# ---------------------------------------------------------------------------
# Tests — _parse_binary (SNAP_QUOTE mode)
# ---------------------------------------------------------------------------


def test_snap_quote_includes_oi_and_depth() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    data = _ao_snap_quote_packet(
        TOKEN_STR, ltp_paise=2000_00,
        oi=5000, bid_paise=1999_00, ask_paise=2001_00,
    )

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.ltp    == pytest.approx(2000.0)
    assert tick.oi     == 5000
    assert tick.bid    == pytest.approx(1999.0)
    assert tick.ask    == pytest.approx(2001.0)


def test_snap_quote_zero_bid_ask_stays_none() -> None:
    ws = _ws_with_token(TOKEN_STR, INSTR)
    data = _ao_snap_quote_packet(TOKEN_STR, ltp_paise=100_00, bid_paise=0, ask_paise=0)

    tick = ws._parse_binary(data)

    assert tick is not None
    assert tick.bid is None
    assert tick.ask is None


# ---------------------------------------------------------------------------
# Tests — _parse_best5_top
# ---------------------------------------------------------------------------


def test_parse_best5_returns_bid_and_ask() -> None:
    block = bytearray(200)
    # Entry 0: flag=0 (buy), price=₹1999
    struct.pack_into("<HqqH", block, 0,  0,   10, 1999_00, 1)
    # Entry 1: flag=1 (sell), price=₹2001
    struct.pack_into("<HqqH", block, 20, 1,   10, 2001_00, 1)

    bid, ask = AngelOneWebSocket._parse_best5_top(bytes(block))

    assert bid == pytest.approx(1999.0)
    assert ask == pytest.approx(2001.0)


def test_parse_best5_skips_zero_prices() -> None:
    block = bytearray(200)
    # Entry 0: buy with price=0 (should be skipped)
    struct.pack_into("<HqqH", block, 0,  0, 5, 0, 1)
    # Entry 1: buy with real price
    struct.pack_into("<HqqH", block, 20, 0, 5, 500_00, 1)
    # Entry 2: sell with real price
    struct.pack_into("<HqqH", block, 40, 1, 5, 505_00, 1)

    bid, ask = AngelOneWebSocket._parse_best5_top(bytes(block))

    assert bid == pytest.approx(500.0)
    assert ask == pytest.approx(505.0)


def test_parse_best5_empty_block_returns_none() -> None:
    bid, ask = AngelOneWebSocket._parse_best5_top(b"")
    assert bid is None
    assert ask is None


# ---------------------------------------------------------------------------
# Tests — _build_token_list
# ---------------------------------------------------------------------------


def test_build_token_list_groups_by_exchange() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    ws._token_exchange_type = {"T1": 1, "T2": 1, "T3": 2}

    result = ws._build_token_list(["T1", "T2", "T3"])

    by_et = {entry["exchangeType"]: entry["tokens"] for entry in result}
    assert set(by_et[1]) == {"T1", "T2"}
    assert by_et[2] == ["T3"]


def test_build_token_list_empty_returns_empty() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    assert ws._build_token_list([]) == []


def test_build_token_list_unknown_token_defaults_exchange_1() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    # No entry in _token_exchange_type — should default to 1

    result = ws._build_token_list(["UNKNOWN"])

    assert result[0]["exchangeType"] == 1


# ---------------------------------------------------------------------------
# Tests — subscribe / unsubscribe
# ---------------------------------------------------------------------------


async def test_subscribe_populates_token_map() -> None:
    from tt_connect.core.store.resolver import ResolvedInstrument

    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    instr = Equity(exchange="NSE", symbol="INFY")
    resolved = ResolvedInstrument(token="1594", broker_symbol="INFY", exchange="NSE")

    async def on_tick(tick):
        pass

    with patch("tt_connect.brokers.angelone.ws.asyncio.create_task"):
        await ws.subscribe([(instr, resolved)], on_tick=on_tick)

    assert ws._token_map["1594"] is instr
    assert ws._token_exchange_type["1594"] == 1  # NSE → exchangeType 1
    assert ws._on_tick is on_tick


async def test_unsubscribe_removes_tokens() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    instr = Equity(exchange="NSE", symbol="INFY")
    ws._token_map["1594"] = instr
    ws._token_exchange_type["1594"] = 1
    ws._ws = None  # not connected — skip network send

    await ws.unsubscribe([instr])

    assert "1594" not in ws._token_map
    assert "1594" not in ws._token_exchange_type


async def test_unsubscribe_no_match_is_noop() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    instr = Equity(exchange="NSE", symbol="INFY")
    # not in token_map

    await ws.unsubscribe([instr])  # should not raise


# ---------------------------------------------------------------------------
# Tests — close
# ---------------------------------------------------------------------------


async def test_close_sets_closed_flag() -> None:
    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)

    await ws.close()

    assert ws._closed is True


async def test_close_cancels_running_task() -> None:
    import asyncio

    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)

    async def _dummy() -> None:
        await asyncio.sleep(10)

    ws._task = asyncio.create_task(_dummy())
    await asyncio.sleep(0)  # let task start

    await ws.close()

    assert ws._task.cancelled() or ws._task.done()


class _FakeWs:
    """Minimal async websocket double for _connect_and_run tests."""

    def __init__(self, messages: list[bytes | str]) -> None:
        self._messages = messages
        self._iter = iter(self._messages)

    async def __aenter__(self) -> "_FakeWs":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def __aiter__(self) -> "_FakeWs":
        self._iter = iter(self._messages)
        return self

    async def __anext__(self) -> bytes | str:
        try:
            return next(self._iter)
        except StopIteration as e:
            raise StopAsyncIteration from e

    async def send(self, data: str) -> None:
        _ = data


async def test_on_tick_exception_is_logged_and_stream_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging
    from unittest.mock import AsyncMock

    auth = MagicMock()
    auth._session = MagicMock(feed_token="feedtok")
    auth.access_token = "accesstok"
    auth._config = {"api_key": "key", "client_id": "cid"}

    ws = AngelOneWebSocket(auth=auth)
    ws._ping_loop = AsyncMock(return_value=None)  # type: ignore[method-assign]

    calls = 0

    async def on_tick(tick: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")

    ws._on_tick = on_tick
    ws._parse_binary = lambda _m: object()  # type: ignore[method-assign]

    with patch("tt_connect.brokers.angelone.ws.websockets.connect", return_value=_FakeWs([b"a", b"b"])):
        with caplog.at_level(logging.ERROR, logger="tt_connect.brokers.angelone.ws"):
            await ws._connect_and_run()

    assert calls == 2
    assert "AngelOne WS on_tick callback failed" in caplog.text


async def test_subscribe_requests_snap_quote_mode() -> None:
    """_send_subscribe defaults to SNAP_QUOTE mode (mode=3)."""
    sent: list[str] = []

    class _CapturingWs:
        async def send(self, data: str) -> None:
            sent.append(data)

    auth = MagicMock()
    ws = AngelOneWebSocket(auth=auth)
    ws._token_exchange_type[TOKEN_STR] = 1

    await ws._send_subscribe(_CapturingWs(), [TOKEN_STR])

    msg = json.loads(sent[0])
    assert msg["params"]["mode"] == 3
