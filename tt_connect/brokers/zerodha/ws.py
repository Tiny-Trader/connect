"""Zerodha KiteTicker WebSocket client and binary tick parser."""

from __future__ import annotations

import asyncio
import json
import logging
import struct
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import websockets
import websockets.exceptions

from tt_connect.core.store.resolver import ResolvedInstrument
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.models import Tick
from tt_connect.core.adapter.ws import BrokerWebSocket, OnTick

logger = logging.getLogger(__name__)

_WS_BASE = "wss://ws.kite.trade"

# Subscription modes
_MODE_LTP   = "ltp"
_MODE_QUOTE = "quote"
_MODE_FULL  = "full"

# Packet sizes (big-endian int32 fields, prices in paise)
_LTP_PACKET_LEN   = 8    # token(4) + ltp(4)
_QUOTE_PACKET_LEN = 44   # ltp + ohlc + volume (no depth)
_FULL_PACKET_LEN  = 184  # quote + oi + depth (10 levels)


class ZerodhaWebSocket(BrokerWebSocket):
    """
    Zerodha KiteTicker WebSocket client.

    Connection: wss://ws.kite.trade?api_key=xxx&access_token=yyy

    Subscription requests are JSON:
      {"a": "subscribe", "v": [token, ...]}
      {"a": "mode",      "v": ["quote", [token, ...]]}

    Binary message outer frame (big-endian):
      bytes 0-2:  int16 — number of packets in this message
      for each packet:
        bytes 0-2: int16 — packet length in bytes
        bytes 2-N: packet data

    Quote packet fields (big-endian int32, prices in paise → ÷100):
      0 - 4:   instrument_token
      4 - 8:   last traded price         ← ltp mode ends here (8 bytes)
      8 - 12:  last traded quantity
      12 - 16: average traded price
      16 - 20: volume traded for day
      20 - 24: total buy quantity
      24 - 28: total sell quantity
      28 - 32: open price
      32 - 36: high price
      36 - 40: low price
      40 - 44: close price               ← quote mode ends here (44 bytes)
      44 - 48: last traded timestamp
      48 - 52: open interest
      52 - 56: OI day high
      56 - 60: OI day low
      60 - 64: exchange timestamp
      64 -184: market depth (10 × 12 bytes: 5 bids then 5 asks)
                 each entry: qty(I=4) + price(I=4) + orders(H=2) + pad(2)
                                                     ← full mode ends here (184 bytes)

    Index packet (smaller, no depth):
      0 - 4:  token
      4 - 8:  ltp                        ← ltp ends here (8 bytes)
      8 - 12: high
      12 - 16: low
      16 - 20: open
      20 - 24: close
      24 - 28: price change              ← quote ends here (28 bytes)
      28 - 32: exchange timestamp        ← full ends here (32 bytes)

    A 1-byte message is a server heartbeat — safely ignored.
    """

    MAX_RECONNECT_DELAY = 60  # seconds

    def __init__(self, api_key: str, access_token: str) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._on_tick: OnTick | None = None
        self._closed = False
        self._ws: Any | None = None
        self._task: asyncio.Task[None] | None = None
        self._reconnect_delay = 2.0

        # int token → Instrument — reverse map for incoming binary ticks
        self._token_map: dict[int, Instrument] = {}

    # ------------------------------------------------------------------ public

    async def subscribe(
        self,
        subscriptions: list[tuple[Instrument, ResolvedInstrument]],
        on_tick: OnTick,
    ) -> None:
        """Track subscriptions and ensure the WebSocket loop is running."""
        self._on_tick = on_tick

        new_tokens: list[int] = []
        for instrument, resolved in subscriptions:
            token_int = int(resolved.token)
            self._token_map[token_int] = instrument
            new_tokens.append(token_int)

        if self._task is None or self._task.done():
            self._closed = False
            self._task = asyncio.create_task(self._run())
        elif self._ws is not None:
            # Already connected — subscribe new tokens immediately
            await self._send_subscribe(self._ws, new_tokens)

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        """Unsubscribe instruments and remove them from the token map."""
        tokens = [t for t, inst in self._token_map.items() if inst in instruments]
        if not tokens:
            return
        if self._ws is not None:
            await self._send_unsubscribe(self._ws, tokens)
        for t in tokens:
            self._token_map.pop(t, None)

    async def close(self) -> None:
        """Stop the reconnect loop and cancel the active WebSocket task."""
        self._closed = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ------------------------------------------------------------ main loop

    async def _run(self) -> None:
        """Reconnect loop with exponential backoff."""
        while not self._closed:
            try:
                await self._connect_and_run()
                self._reconnect_delay = 2.0  # reset on clean exit
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(
                    f"Zerodha WS error: {exc}",
                    extra={"event": "ws.error", "broker": "zerodha"},
                )
            if self._closed:
                break
            logger.info(
                f"Zerodha WS reconnecting in {self._reconnect_delay:.0f}s …",
                extra={"event": "ws.reconnect", "broker": "zerodha", "delay_s": self._reconnect_delay},
            )
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY)

    async def _connect_and_run(self) -> None:
        """Open WebSocket, resubscribe all tracked tokens, and dispatch ticks."""
        qs = urlencode({"api_key": self._api_key, "access_token": self._access_token})
        url = f"{_WS_BASE}?{qs}"

        async with websockets.connect(url) as ws:
            self._ws = ws
            logger.info("Zerodha WS connected", extra={"event": "ws.connect", "broker": "zerodha"})

            if self._token_map:
                await self._send_subscribe(ws, list(self._token_map.keys()))

            try:
                async for message in ws:
                    if isinstance(message, bytes):
                        if len(message) == 1:
                            # Server heartbeat — ignore
                            continue
                        for tick in self._parse_binary_message(message):
                            if self._on_tick:
                                try:
                                    await self._on_tick(tick)
                                except Exception:
                                    logger.exception(
                                        "Zerodha WS on_tick callback failed",
                                        extra={"event": "ws.tick_error", "broker": "zerodha"},
                                    )
                    else:
                        self._handle_text(message)
            finally:
                self._ws = None
                logger.info("Zerodha WS disconnected", extra={"event": "ws.disconnect", "broker": "zerodha"})

    # ------------------------------------------------- subscribe / unsubscribe

    async def _send_subscribe(self, ws: Any, tokens: list[int]) -> None:
        """Send subscribe + mode messages for the given token list."""
        await ws.send(json.dumps({"a": "subscribe", "v": tokens}))
        await ws.send(json.dumps({"a": "mode", "v": [_MODE_FULL, tokens]}))
        logger.debug(
            f"Subscribed to {len(tokens)} tokens (mode={_MODE_FULL})",
            extra={"event": "ws.subscribe", "broker": "zerodha", "token_count": len(tokens), "mode": _MODE_FULL},
        )

    async def _send_unsubscribe(self, ws: Any, tokens: list[int]) -> None:
        await ws.send(json.dumps({"a": "unsubscribe", "v": tokens}))
        logger.debug(
            f"Unsubscribed from {len(tokens)} tokens",
            extra={"event": "ws.unsubscribe", "broker": "zerodha", "token_count": len(tokens)},
        )

    # ------------------------------------------------------ binary parser

    def _parse_binary_message(self, data: bytes) -> list[Tick]:
        """
        Parse a KiteTicker binary message into a list of canonical Ticks.

        The message may contain multiple quote packets, framed as:
          [num_packets: int16][pkt_len: int16][packet bytes] ...
        """
        if len(data) < 2:
            return []

        ticks: list[Tick] = []
        num_packets = struct.unpack_from(">H", data, 0)[0]
        offset = 2

        for _ in range(num_packets):
            if offset + 2 > len(data):
                break
            pkt_len = struct.unpack_from(">H", data, offset)[0]
            offset += 2
            if offset + pkt_len > len(data):
                break
            packet = data[offset: offset + pkt_len]
            offset += pkt_len
            tick = self._parse_packet(packet)
            if tick is not None:
                ticks.append(tick)

        return ticks

    def _parse_packet(self, packet: bytes) -> Tick | None:
        """Parse one KiteTicker quote packet into a canonical Tick."""
        pkt_len = len(packet)
        if pkt_len < _LTP_PACKET_LEN:
            return None

        token_int = struct.unpack_from(">I", packet, 0)[0]
        instrument = self._token_map.get(token_int)
        if instrument is None:
            logger.debug(f"Tick for unknown token {token_int}")
            return None

        ltp = struct.unpack_from(">I", packet, 4)[0] / 100.0

        volume: int | None = None
        oi: int | None     = None
        bid: float | None  = None
        ask: float | None  = None
        ts: datetime | None = None

        if pkt_len >= _QUOTE_PACKET_LEN:
            volume = struct.unpack_from(">I", packet, 16)[0]

        if pkt_len >= _FULL_PACKET_LEN:
            oi = struct.unpack_from(">I", packet, 48)[0]
            ts_epoch = struct.unpack_from(">I", packet, 60)[0]
            if ts_epoch > 0:
                ts = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
            bid, ask = self._parse_depth_top(packet[64:184])

        return Tick(
            instrument=instrument,
            ltp=ltp,
            volume=volume,
            oi=oi,
            bid=bid,
            ask=ask,
            timestamp=ts,
        )

    @staticmethod
    def _parse_depth_top(depth_block: bytes) -> tuple[float | None, float | None]:
        """
        Parse 120 bytes of market depth into (best_bid, best_ask).

        Depth layout: 5 bid entries (bytes 0-60) then 5 ask entries (bytes 60-120).
        Each 12-byte entry: quantity(I=4) + price(I=4) + orders(H=2) + padding(2).
        Prices are in paise; divide by 100 for rupees.
        """
        bid: float | None = None
        ask: float | None = None

        for i in range(5):
            offset = i * 12
            if offset + 12 > len(depth_block):
                break
            price = struct.unpack_from(">I", depth_block, offset + 4)[0] / 100.0
            if price > 0 and bid is None:
                bid = price

        for i in range(5):
            offset = 60 + i * 12
            if offset + 12 > len(depth_block):
                break
            price = struct.unpack_from(">I", depth_block, offset + 4)[0] / 100.0
            if price > 0 and ask is None:
                ask = price

        return bid, ask

    def _handle_text(self, message: str) -> None:
        """Handle non-binary text messages (order updates, errors, broker alerts)."""
        try:
            data = json.loads(message)
        except Exception:
            return
        msg_type = data.get("type")
        if msg_type == "error":
            logger.error(f"Zerodha WS error message: {data.get('data')}")
        elif msg_type == "message":
            logger.info(f"Zerodha WS broker message: {data.get('data')}")
        # "order" type — future: route to on_order_update callback
