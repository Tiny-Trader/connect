"""Adapter SPI — everything a broker implementor needs to extend."""

from tt_connect.core.adapter.auth import (
    BaseAuth,
    BaseSessionStore,
    FileSessionStore,
    MemorySessionStore,
    SessionData,
    next_midnight_ist,
)
from tt_connect.core.adapter.base import BrokerAdapter
from tt_connect.core.adapter.capabilities import Capabilities
from tt_connect.core.adapter.transformer import BrokerTransformer, JsonDict
from tt_connect.core.adapter.ws import BrokerWebSocket, OnTick

__all__ = [
    "BaseAuth",
    "BaseSessionStore",
    "BrokerAdapter",
    "BrokerTransformer",
    "BrokerWebSocket",
    "Capabilities",
    "FileSessionStore",
    "JsonDict",
    "MemorySessionStore",
    "OnTick",
    "SessionData",
    "next_midnight_ist",
]
