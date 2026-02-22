"""AngelOne SmartStream WebSocket client and binary tick parser."""

from __future__ import annotations

import asyncio
import json
import logging
import struct
from datetime import datetime, timezone
from typing import Any

import websockets
import websockets.exceptions

from tt_connect.instrument_manager.resolver import ResolvedInstrument
from tt_connect.instruments import Instrument
from tt_connect.models import Tick
from tt_connect.ws.client import BrokerWebSocket, OnTick

logger = logging.getLogger(__name__)

_WS_URL = "wss://smartapisocket.angelone.in/smart-stream"

# Exchange → AngelOne exchangeType integer
_EXCHANGE_TYPE: dict[str, int] = {
    "NSE": 1,
    "NFO": 2,
    "BSE": 3,
    "BFO": 4,
    "MCX": 5,
}

# Subscription modes
_MODE_LTP        = 1
_MODE_QUOTE      = 2
_MODE_SNAP_QUOTE = 3

# Minimum packet sizes per mode (little-endian binary)
_LTP_MIN        = 51   # bytes 0-50
_QUOTE_MIN      = 123  # bytes 0-122
_SNAP_QUOTE_MIN = 347  # bytes 0-346 (need best_5 block to parse bid/ask)


class AngelOneWebSocket(BrokerWebSocket):
    """
    AngelOne SmartStream WebSocket client.

    Binary protocol (little-endian):
      byte  0:     subscription_mode (B)
      byte  1:     exchange_type (B)
      bytes 2-26:  token (25-byte null-terminated ASCII)
      bytes 27-34: sequence_number (q)
      bytes 35-42: exchange_timestamp (q, milliseconds)
      bytes 43-50: last_traded_price (q, paise → ÷100)

      QUOTE (mode≥2, ≥123 bytes) adds:
        bytes 51-58:   last_traded_quantity (q)
        bytes 59-66:   average_traded_price (q, paise)
        bytes 67-74:   volume_trade_for_the_day (q)
        bytes 75-82:   total_buy_quantity (d)
        bytes 83-90:   total_sell_quantity (d)
        bytes 91-98:   open_price (q, paise)
        bytes 99-106:  high_price (q, paise)
        bytes 107-114: low_price (q, paise)
        bytes 115-122: closed_price (q, paise)

      SNAP_QUOTE (mode=3, ≥347 bytes) adds:
        bytes 123-130: last_traded_timestamp (q)
        bytes 131-138: open_interest (q)
        bytes 139-146: oi_change_percentage (q)
        bytes 147-346: best_5_buy_sell (200 bytes, 10×20)
                       each 20-byte packet: flag(H) qty(q) price(q) orders(H)
                       flag==0 → buy side, flag!=0 → sell side
    """

    PING_INTERVAL       = 10    # seconds between heartbeat pings
    MAX_RECONNECT_DELAY = 60    # seconds

    def __init__(self, auth: Any) -> None:
        # auth: AngelOneAuth (typed loosely to avoid circular import)
        self._auth = auth
        self._on_tick: OnTick | None = None
        self._closed = False
        self._ws: Any | None = None
        self._task: asyncio.Task[None] | None = None
        self._reconnect_delay = 2.0

        # token (str) → Instrument  — reverse map for incoming ticks
        self._token_map: dict[str, Instrument] = {}
        # token (str) → exchangeType (int) — needed to build subscribe messages
        self._token_exchange_type: dict[str, int] = {}

    # ------------------------------------------------------------------ public

    async def subscribe(
        self,
        subscriptions: list[tuple[Instrument, ResolvedInstrument]],
        on_tick: OnTick,
    ) -> None:
        """Track subscriptions and ensure websocket loop is running."""
        self._on_tick = on_tick

        new_tokens: list[str] = []
        for instrument, resolved in subscriptions:
            self._token_map[resolved.token] = instrument
            self._token_exchange_type[resolved.token] = _EXCHANGE_TYPE.get(resolved.exchange, 1)
            new_tokens.append(resolved.token)

        if self._task is None or self._task.done():
            self._closed = False
            self._task = asyncio.create_task(self._run())
        elif self._ws is not None:
            # Already connected — subscribe new tokens immediately
            await self._send_subscribe(self._ws, new_tokens)

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        """Unsubscribe instruments and prune local token maps."""
        tokens = [t for t, inst in self._token_map.items() if inst in instruments]
        if not tokens:
            return
        if self._ws is not None:
            await self._send_unsubscribe(self._ws, tokens)
        for t in tokens:
            self._token_map.pop(t, None)
            self._token_exchange_type.pop(t, None)

    async def close(self) -> None:
        """Stop reconnect loop and close active websocket task."""
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
                logger.warning(f"AngelOne WS error: {exc}")
            if self._closed:
                break
            logger.info(f"AngelOne WS reconnecting in {self._reconnect_delay:.0f}s …")
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY)

    async def _connect_and_run(self) -> None:
        """Open websocket, resubscribe tracked tokens, and dispatch ticks."""
        if not self._auth._session:
            raise RuntimeError("AngelOne auth session not available — call login() first")

        headers = {
            "Authorization":  self._auth.access_token,
            "x-api-key":      self._auth._config.get("api_key", ""),
            "x-client-code":  self._auth._config.get("client_id", ""),
            "x-feed-token":   self._auth._session.feed_token or "",
        }

        async with websockets.connect(_WS_URL, additional_headers=headers) as ws:
            self._ws = ws
            logger.info("AngelOne WS connected")

            # On (re)connect, resubscribe to everything currently tracked
            if self._token_map:
                await self._send_subscribe(ws, list(self._token_map.keys()))

            ping_task: asyncio.Task[None] = asyncio.create_task(self._ping_loop(ws))
            try:
                async for message in ws:
                    if isinstance(message, bytes):
                        tick = self._parse_binary(message)
                        if tick and self._on_tick:
                            await self._on_tick(tick)
                    # text "pong" — ignore
            finally:
                ping_task.cancel()
                self._ws = None
                logger.info("AngelOne WS disconnected")

    async def _ping_loop(self, ws: Any) -> None:
        """Send periodic ping text frames to keep the socket alive."""
        while True:
            await asyncio.sleep(self.PING_INTERVAL)
            try:
                await ws.send("ping")
            except Exception:
                break

    # ------------------------------------------------- subscribe / unsubscribe

    async def _send_subscribe(
        self, ws: Any, tokens: list[str], mode: int = _MODE_QUOTE
    ) -> None:
        token_list = self._build_token_list(tokens)
        if not token_list:
            return
        await ws.send(json.dumps({
            "correlationID": "ttconnect",
            "action": 1,
            "params": {"mode": mode, "tokenList": token_list},
        }))
        logger.debug(f"Subscribed to {len(tokens)} tokens (mode={mode})")

    async def _send_unsubscribe(
        self, ws: Any, tokens: list[str], mode: int = _MODE_QUOTE
    ) -> None:
        token_list = self._build_token_list(tokens)
        if not token_list:
            return
        await ws.send(json.dumps({
            "correlationID": "ttconnect",
            "action": 0,
            "params": {"mode": mode, "tokenList": token_list},
        }))
        logger.debug(f"Unsubscribed from {len(tokens)} tokens")

    def _build_token_list(self, tokens: list[str]) -> list[dict[str, Any]]:
        """Group tokens by exchangeType for the AngelOne subscribe payload."""
        by_exchange: dict[int, list[str]] = {}
        for token in tokens:
            et = self._token_exchange_type.get(token, 1)
            by_exchange.setdefault(et, []).append(token)
        return [
            {"exchangeType": et, "tokens": toks}
            for et, toks in by_exchange.items()
        ]

    # ------------------------------------------------------ binary parser

    def _parse_binary(self, data: bytes) -> Tick | None:
        """Parse one binary SmartStream packet into canonical Tick."""
        if len(data) < _LTP_MIN:
            return None

        subscription_mode = data[0]
        token = data[2:27].split(b"\x00")[0].decode("ascii", errors="replace").strip()

        instrument = self._token_map.get(token)
        if instrument is None:
            logger.debug(f"Tick for unknown token {token!r}")
            return None

        ts_ms  = struct.unpack_from("<q", data, 35)[0]
        ltp    = struct.unpack_from("<q", data, 43)[0] / 100.0
        ts     = (
            datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            if ts_ms > 0 else None
        )

        volume: int | None = None
        oi: int | None     = None
        bid: float | None  = None
        ask: float | None  = None

        if subscription_mode >= _MODE_QUOTE and len(data) >= _QUOTE_MIN:
            volume = struct.unpack_from("<q", data, 67)[0]

        if subscription_mode >= _MODE_SNAP_QUOTE and len(data) >= _SNAP_QUOTE_MIN:
            oi = struct.unpack_from("<q", data, 131)[0]
            bid, ask = self._parse_best5_top(data[147:347])

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
    def _parse_best5_top(block: bytes) -> tuple[float | None, float | None]:
        """
        Parse the 200-byte best-5 block and return (best_bid, best_ask).

        Each 20-byte packet:  flag(H=2) | quantity(q=8) | price(q=8) | orders(H=2)
        flag == 0  → buy side (we want the first one = highest bid)
        flag != 0  → sell side (we want the first one = lowest ask)
        Prices are in paise; divide by 100 for rupees.
        """
        bid: float | None = None
        ask: float | None = None
        for i in range(10):
            offset = i * 20
            if offset + 20 > len(block):
                break
            flag, _qty, price_paise, _orders = struct.unpack_from("<HqqH", block, offset)
            price = price_paise / 100.0
            if price <= 0:
                continue
            if flag == 0 and bid is None:
                bid = price
            elif flag != 0 and ask is None:
                ask = price
            if bid is not None and ask is not None:
                break
        return bid, ask
