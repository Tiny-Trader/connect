"""Unit tests for the Zerodha KiteTicker binary parser."""

from __future__ import annotations

import json
import struct
from tt_connect.core.timezone import IST
import pytest

from tt_connect.core.models.instruments import Equity
from tt_connect.brokers.zerodha.ws import ZerodhaWebSocket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_ltp_packet(token: int, ltp_paise: int) -> bytes:
    """Build an 8-byte LTP-mode packet."""
    return struct.pack(">II", token, ltp_paise)


def _build_quote_packet(
    token: int,
    ltp_paise: int,
    last_qty: int = 10,
    avg_price_paise: int = 0,
    volume: int = 500,
    buy_qty: int = 100,
    sell_qty: int = 200,
    open_paise: int = 0,
    high_paise: int = 0,
    low_paise: int = 0,
    close_paise: int = 0,
) -> bytes:
    """Build a 44-byte quote-mode packet."""
    return struct.pack(
        ">IIIIIIIIIII",
        token, ltp_paise, last_qty, avg_price_paise, volume,
        buy_qty, sell_qty, open_paise, high_paise, low_paise, close_paise,
    )


def _build_full_packet(
    token: int,
    ltp_paise: int,
    volume: int = 500,
    oi: int = 100,
    exchange_ts: int = 1700000000,
    best_bid_paise: int = 249900,
    best_ask_paise: int = 250100,
) -> bytes:
    """Build a 184-byte full-mode packet with synthetic depth."""
    # quote portion (44 bytes)
    quote = struct.pack(
        ">IIIIIIIIIII",
        token, ltp_paise, 0, 0, volume, 0, 0, 0, 0, 0, 0,
    )
    # extra full fields: ltt(4) + oi(4) + oi_hi(4) + oi_lo(4) + exch_ts(4) = 20 bytes
    extra = struct.pack(">IIIII", 0, oi, 0, 0, exchange_ts)
    # depth: 5 bid entries + 5 ask entries, each 12 bytes
    # entry format: qty(I=4) + price(I=4) + orders(H=2) + pad(2)
    bid_entry = struct.pack(">IIH2s", 10, best_bid_paise, 1, b"\x00\x00")
    ask_entry = struct.pack(">IIH2s", 10, best_ask_paise, 1, b"\x00\x00")
    depth = bid_entry * 5 + ask_entry * 5  # 60 + 60 = 120 bytes
    return quote + extra + depth  # 44 + 20 + 120 = 184 bytes


def _frame(*packets: bytes) -> bytes:
    """Wrap packets into a KiteTicker binary message frame."""
    header = struct.pack(">H", len(packets))
    body = b"".join(
        struct.pack(">H", len(p)) + p for p in packets
    )
    return header + body


def _ws_with_instrument(token: int, instrument: Equity) -> ZerodhaWebSocket:
    """Return a ZerodhaWebSocket pre-seeded with a token→instrument mapping."""
    ws = ZerodhaWebSocket(api_key="key", access_token="tok")
    ws._token_map[token] = instrument
    return ws


# ---------------------------------------------------------------------------
# Tests — binary parser
# ---------------------------------------------------------------------------

TOKEN = 408065
INSTR = Equity(exchange="NSE", symbol="INFY")


def test_ltp_packet_parsed_correctly() -> None:
    ltp_paise = 175050  # ₹1750.50
    ws = _ws_with_instrument(TOKEN, INSTR)
    packet = _build_ltp_packet(TOKEN, ltp_paise)
    msg = _frame(packet)

    ticks = ws._parse_binary_message(msg)

    assert len(ticks) == 1
    assert ticks[0].ltp == pytest.approx(1750.50)
    assert ticks[0].volume is None
    assert ticks[0].oi is None
    assert ticks[0].bid is None
    assert ticks[0].ask is None
    assert ticks[0].instrument is INSTR


def test_quote_packet_includes_volume() -> None:
    ws = _ws_with_instrument(TOKEN, INSTR)
    packet = _build_quote_packet(TOKEN, ltp_paise=25000_00, volume=12345)
    msg = _frame(packet)

    ticks = ws._parse_binary_message(msg)

    assert len(ticks) == 1
    assert ticks[0].ltp == pytest.approx(25000.00)
    assert ticks[0].volume == 12345
    assert ticks[0].oi is None


def test_full_packet_includes_oi_and_depth() -> None:
    ws = _ws_with_instrument(TOKEN, INSTR)
    packet = _build_full_packet(
        TOKEN,
        ltp_paise=250000,
        oi=5000,
        best_bid_paise=249900,
        best_ask_paise=250100,
    )
    msg = _frame(packet)

    ticks = ws._parse_binary_message(msg)

    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.ltp == pytest.approx(2500.00)
    assert tick.oi == 5000
    assert tick.bid == pytest.approx(2499.00)
    assert tick.ask == pytest.approx(2501.00)


def test_multi_packet_message() -> None:
    TOKEN2 = 884737
    INSTR2 = Equity(exchange="NSE", symbol="TATAMOTORS")
    ws = _ws_with_instrument(TOKEN, INSTR)
    ws._token_map[TOKEN2] = INSTR2

    p1 = _build_ltp_packet(TOKEN, 100_00)
    p2 = _build_ltp_packet(TOKEN2, 200_00)
    msg = _frame(p1, p2)

    ticks = ws._parse_binary_message(msg)

    assert len(ticks) == 2
    assert ticks[0].instrument is INSTR
    assert ticks[0].ltp == pytest.approx(100.0)
    assert ticks[1].instrument is INSTR2
    assert ticks[1].ltp == pytest.approx(200.0)


def test_one_byte_heartbeat_produces_no_ticks() -> None:
    ws = _ws_with_instrument(TOKEN, INSTR)
    # The heartbeat guard is in _connect_and_run; _parse_binary_message handles
    # remaining edge cases (empty frame).
    result = ws._parse_binary_message(b"\x00")
    assert result == []


def test_unknown_token_skipped() -> None:
    ws = ZerodhaWebSocket(api_key="key", access_token="tok")
    # Token map is empty — no instrument registered
    packet = _build_ltp_packet(99999, 100_00)
    msg = _frame(packet)

    ticks = ws._parse_binary_message(msg)
    assert ticks == []


def test_full_packet_timestamp() -> None:
    ws = _ws_with_instrument(TOKEN, INSTR)
    ts_epoch = 1700000000
    packet = _build_full_packet(TOKEN, ltp_paise=100_00, exchange_ts=ts_epoch)
    msg = _frame(packet)

    ticks = ws._parse_binary_message(msg)

    assert len(ticks) == 1
    assert ticks[0].timestamp is not None
    assert ticks[0].timestamp.tzinfo == IST


def test_empty_message_returns_empty() -> None:
    ws = _ws_with_instrument(TOKEN, INSTR)
    assert ws._parse_binary_message(b"") == []


def test_text_error_message_logged(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    ws = ZerodhaWebSocket(api_key="key", access_token="tok")
    with caplog.at_level(logging.ERROR, logger="tt_connect.brokers.zerodha.ws"):
        ws._handle_text('{"type": "error", "data": "Rate limit exceeded"}')
    assert "Rate limit exceeded" in caplog.text


def test_text_broker_message_logged(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    ws = ZerodhaWebSocket(api_key="key", access_token="tok")
    with caplog.at_level(logging.INFO, logger="tt_connect.brokers.zerodha.ws"):
        ws._handle_text('{"type": "message", "data": "Market closed"}')
    assert "Market closed" in caplog.text


def test_depth_all_zero_prices_returns_none() -> None:
    """If all depth prices are zero, bid and ask stay None."""
    ws = _ws_with_instrument(TOKEN, INSTR)
    # Build a full packet with zero depth prices
    quote = struct.pack(">IIIIIIIIIII", TOKEN, 100_00, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    extra = struct.pack(">IIIII", 0, 0, 0, 0, 0)
    # All depth entries have price=0
    zero_entry = struct.pack(">IIH2s", 0, 0, 0, b"\x00\x00")
    depth = zero_entry * 10
    packet = quote + extra + depth

    msg = _frame(packet)
    ticks = ws._parse_binary_message(msg)

    assert len(ticks) == 1
    assert ticks[0].bid is None
    assert ticks[0].ask is None


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
    from unittest.mock import patch

    ws = ZerodhaWebSocket(api_key="key", access_token="tok")
    calls = 0

    async def on_tick(tick: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")

    ws._on_tick = on_tick
    ws._parse_binary_message = lambda _m: [object(), object()]  # type: ignore[method-assign]

    with patch("tt_connect.brokers.zerodha.ws.websockets.connect", return_value=_FakeWs([b"ab"])):
        with caplog.at_level(logging.ERROR, logger="tt_connect.brokers.zerodha.ws"):
            await ws._connect_and_run()

    assert calls == 2
    assert "Zerodha WS on_tick callback failed" in caplog.text


async def test_subscribe_requests_full_mode() -> None:
    """_send_subscribe sends mode=full, not mode=quote."""
    sent: list[str] = []

    class _CapturingWs:
        async def send(self, data: str) -> None:
            sent.append(data)

    ws = ZerodhaWebSocket(api_key="key", access_token="tok")
    await ws._send_subscribe(_CapturingWs(), [408065])

    # Second message sets the subscription mode
    mode_msg = json.loads(sent[1])
    assert mode_msg["a"] == "mode"
    assert mode_msg["v"][0] == "full"
