"""Shared state and abstract interface for all client mixins.

Every mixin (lifecycle, portfolio, orders, instruments) extends
``_ClientBase`` so that type checkers know which attributes and
helper methods are available on ``self``. The concrete implementation
lives in ``_lifecycle.py`` (``LifecycleMixin``), which initializes
all the state declared here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tt_connect.core.adapter.base import BrokerAdapter
from tt_connect.core.adapter.ws import BrokerWebSocket
from tt_connect.core.models.enums import ClientState
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.store.manager import InstrumentManager
from tt_connect.core.store.resolver import InstrumentResolver, ResolvedInstrument


class _ClientBase(ABC):
    """Declares shared state and abstract interface used by all client mixins.

    This class exists purely as a type-checking contract. It tells mypy
    (and other mixins) which attributes and methods will be present at
    runtime, even though the actual initialization happens in
    ``LifecycleMixin.__init__``.

    Attributes:
        _broker_id: Identifier of the connected broker (e.g. ``"zerodha"``).
        _adapter: The broker's REST adapter instance.
        _instrument_manager: SQLite-backed instrument store manager.
        _resolver: Token/symbol resolver — ``None`` until ``init()`` completes.
        _ws: WebSocket client — ``None`` until ``subscribe()`` is called.
        _state: Current client lifecycle state (CREATED → CONNECTED → CLOSED).
    """

    _broker_id: str
    _adapter: BrokerAdapter
    _instrument_manager: InstrumentManager
    _resolver: InstrumentResolver | None
    _ws: BrokerWebSocket | None
    _state: ClientState

    @abstractmethod
    def _require_connected(self) -> None:
        """Raise if the client is not in CONNECTED state."""
        ...

    @abstractmethod
    async def _resolve(self, instrument: Instrument) -> ResolvedInstrument:
        """Resolve a canonical instrument to broker-specific execution metadata."""
        ...
