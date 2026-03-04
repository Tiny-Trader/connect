"""Unit tests for LifecycleMixin lifecycle edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from tt_connect.core.models.enums import ClientState
from tt_connect.core.client._lifecycle import LifecycleMixin


class _FakeLifecycle(LifecycleMixin):
    """Thin test double exposing LifecycleMixin behavior."""


def _make_client(state: ClientState, resolver_set: bool = False) -> _FakeLifecycle:
    client: _FakeLifecycle = object.__new__(_FakeLifecycle)
    client._state = state
    client._broker_id = "test"
    client._ws = None
    client._resolver = object() if resolver_set else None
    client._instrument_manager = MagicMock()
    client._instrument_manager.connection.close = AsyncMock()
    client._adapter = MagicMock()
    client._adapter._client.aclose = AsyncMock()
    return client


async def test_close_before_init_does_not_touch_instrument_db() -> None:
    client = _make_client(ClientState.CREATED, resolver_set=False)

    await client.close()

    assert client._state == ClientState.CLOSED
    client._instrument_manager.connection.close.assert_not_awaited()
    client._adapter._client.aclose.assert_awaited_once()


async def test_close_after_init_closes_instrument_db_and_http_client() -> None:
    client = _make_client(ClientState.CONNECTED, resolver_set=True)

    await client.close()

    assert client._state == ClientState.CLOSED
    client._instrument_manager.connection.close.assert_awaited_once()
    client._adapter._client.aclose.assert_awaited_once()
