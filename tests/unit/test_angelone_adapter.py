"""Unit tests for AngelOne adapter method-level behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from tt_connect.brokers.angelone.adapter import AngelOneAdapter
from tt_connect.core.adapter.auth import SessionData


@pytest.mark.asyncio
async def test_modify_gtt_uses_method_gtt_id_over_payload_id() -> None:
    adapter = AngelOneAdapter(
        {
            "auth_mode": "auto",
            "api_key": "k",
            "client_id": "c",
            "pin": "1234",
            "totp_secret": "ABC",
        }
    )

    adapter.auth._session = SessionData(access_token="jwt-token")
    adapter._request = AsyncMock(return_value={"status": True})  # type: ignore[method-assign]

    await adapter.modify_gtt("42", {"id": "WRONG", "price": "100"})

    adapter._request.assert_awaited_once()
    kwargs = adapter._request.await_args.kwargs
    assert kwargs["json"]["id"] == "42"
    assert kwargs["json"]["price"] == "100"
