from __future__ import annotations
from typing import Callable, Awaitable
from tt_connect.instruments import Instrument
from tt_connect.models import Tick


OnTick = Callable[[Tick], Awaitable[None]]


class WebSocketClient:
    def __init__(self, broker_id: str, auth):
        self._broker_id = broker_id
        self._auth = auth

    async def subscribe(
        self,
        instruments: list[Instrument],
        on_tick: OnTick,
        on_order_update: OnTick | None = None,
    ) -> None:
        raise NotImplementedError

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        raise NotImplementedError

    async def _connect(self) -> None:
        raise NotImplementedError

    async def _reconnect(self) -> None:
        raise NotImplementedError
