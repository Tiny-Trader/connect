"""Lifecycle mixin: init, close, state guards, and WebSocket subscribe."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Self

from tt_connect.core.adapter.base import BrokerAdapter
from tt_connect.core.models.enums import ClientState, OnStale
from tt_connect.core.exceptions import ClientClosedError, ClientNotConnectedError
from tt_connect.core.store.manager import InstrumentManager
from tt_connect.core.store.resolver import InstrumentResolver, ResolvedInstrument
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.adapter.ws import BrokerWebSocket, OnTick
from tt_connect.core.logging import log_deprecated_config_keys, log_package_startup

logger = logging.getLogger(__name__)


class _ClientBase(ABC):
    """Declares shared state and abstract interface used by all client mixins."""

    _broker_id: str
    _adapter: BrokerAdapter
    _instrument_manager: InstrumentManager
    _resolver: InstrumentResolver | None
    _ws: BrokerWebSocket | None
    _state: ClientState

    @abstractmethod
    def _require_connected(self) -> None: ...

    @abstractmethod
    async def _resolve(self, instrument: Instrument) -> ResolvedInstrument: ...


class LifecycleMixin(_ClientBase):
    """Lifecycle management: init, close, state guards, and WebSocket subscribe."""

    def __init__(self, broker: str, config: dict[str, Any]) -> None:
        log_package_startup(broker, config)
        log_deprecated_config_keys(config)
        self._broker_id: str = broker
        self._adapter: BrokerAdapter = BrokerAdapter._registry[broker](config)
        self._instrument_manager: InstrumentManager = InstrumentManager(
            broker_id=broker,
            on_stale=config.get("on_stale", OnStale.FAIL),
        )
        self._resolver: InstrumentResolver | None = None
        self._ws: BrokerWebSocket | None = None
        self._state: ClientState = ClientState.CREATED

    def _require_connected(self) -> None:
        """Raise a descriptive error if the client is not in CONNECTED state."""
        if self._state == ClientState.CLOSED:
            raise ClientClosedError("Client has been closed and cannot be reused.")
        if self._state != ClientState.CONNECTED:
            raise ClientNotConnectedError(
                "Client must be connected before this operation. Call await client.init() first."
            )

    async def init(self) -> None:
        """Authenticate and initialize a fresh/stale-safe instrument resolver."""
        await self._adapter.login()
        await self._instrument_manager.init(self._adapter.fetch_instruments)
        self._resolver = InstrumentResolver(
            self._instrument_manager.connection,
            self._broker_id,
        )
        self._state = ClientState.CONNECTED
        logger.info(
            "client connected",
            extra={"event": "client.state_change", "broker": self._broker_id, "state": "connected"},
        )

    async def close(self) -> None:
        """Close WebSocket (if open), instrument DB connection, and HTTP client."""
        if self._state == ClientState.CLOSED:
            return
        self._state = ClientState.CLOSED
        logger.info(
            "client closed",
            extra={"event": "client.state_change", "broker": self._broker_id, "state": "closed"},
        )
        if self._ws:
            await self._ws.close()
        # close() may be called before init() completes; DB connection exists only
        # after resolver/manager initialization succeeds.
        if self._resolver is not None:
            await self._instrument_manager.connection.close()
        await self._adapter._client.aclose()

    async def __aenter__(self) -> Self:
        await self.init()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def _resolve(self, instrument: Instrument) -> ResolvedInstrument:
        """Resolve a canonical instrument to broker token/symbol/exchange."""
        self._require_connected()
        assert self._resolver is not None  # guaranteed: set before CONNECTED state
        return await self._resolver.resolve(instrument)

    # --- Streaming ---

    async def subscribe(
        self,
        instruments: list[Instrument],
        on_tick: OnTick,
    ) -> None:
        """Subscribe to ticks for canonical instruments."""
        self._require_connected()
        if not self._ws:
            self._ws = self._adapter.create_ws_client()
        subscriptions = [
            (instrument, await self._resolve(instrument)) for instrument in instruments
        ]
        await self._ws.subscribe(subscriptions, on_tick)

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        """Unsubscribe previously subscribed instruments."""
        self._require_connected()
        if self._ws:
            await self._ws.unsubscribe(instruments)
