from __future__ import annotations

from abc import abstractmethod
from typing import Callable, Awaitable

from tt_connect.instrument_manager.resolver import ResolvedInstrument
from tt_connect.instruments import Instrument
from tt_connect.models import Tick

# Callback type: async function that receives a Tick
OnTick = Callable[[Tick], Awaitable[None]]


class BrokerWebSocket:
    """Abstract interface for broker-specific streaming implementations."""

    @abstractmethod
    async def subscribe(
        self,
        subscriptions: list[tuple[Instrument, ResolvedInstrument]],
        on_tick: OnTick,
    ) -> None:
        """Start or extend subscriptions and emit normalized ticks via callback."""
        ...

    @abstractmethod
    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        """Remove subscriptions for the provided canonical instruments."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close socket connection and release broker-stream resources."""
        ...
