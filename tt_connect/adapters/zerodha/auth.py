"""Zerodha authentication implementation."""

from __future__ import annotations

from tt_connect.auth.base import BaseAuth, SessionData, next_midnight_ist
from tt_connect.enums import AuthMode
from tt_connect.exceptions import AuthenticationError


class ZerodhaAuth(BaseAuth):
    """Manual-token auth flow for Zerodha."""

    _broker_id = "zerodha"
    _default_mode = AuthMode.MANUAL
    _supported_modes = frozenset({AuthMode.MANUAL})

    async def _login_manual(self) -> None:
        """Load `access_token` from config and create session state."""
        token = self._config.get("access_token")
        if not token:
            raise AuthenticationError(
                "Zerodha requires 'access_token' in config. "
                "Obtain it from https://kite.trade/connect/login?api_key=<your_key>&v=3"
            )
        self._session = SessionData(
            access_token=token,
            expires_at=next_midnight_ist(),
        )

    @property
    def headers(self) -> dict:
        """Build authenticated headers expected by Kite APIs."""
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self._config['api_key']}:{self.access_token}",
        }
