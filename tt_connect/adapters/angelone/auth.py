"""AngelOne authentication implementation."""

from __future__ import annotations

import logging
import socket
from typing import cast

import pyotp

from tt_connect.auth.base import BaseAuth, SessionData, next_midnight_ist
from tt_connect.enums import AuthMode
from tt_connect.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

_LOGIN_URL = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
_RENEW_URL = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/renewToken"


def _local_ip() -> str:
    """Best-effort local IPv4 discovery required by AngelOne headers."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = str(s.getsockname()[0])
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _base_headers(api_key: str) -> dict[str, str]:
    """Build mandatory SmartAPI headers shared across auth and REST calls."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": _local_ip(),
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": api_key,
    }


class AngelOneAuth(BaseAuth):
    """Manual + auto auth implementation for AngelOne SmartAPI."""

    _broker_id       = "angelone"
    _default_mode    = AuthMode.AUTO
    _supported_modes = frozenset({AuthMode.AUTO, AuthMode.MANUAL})

    async def _login_auto(self) -> None:
        """Perform TOTP-based SmartAPI login flow."""
        client_id   = self._config.get("client_id")
        pin         = self._config.get("pin")
        totp_secret = self._config.get("totp_secret")
        api_key     = self._config.get("api_key")

        if not all([client_id, pin, totp_secret, api_key]):
            raise AuthenticationError(
                "AngelOne auto login requires 'client_id', 'pin', 'totp_secret', 'api_key' in config."
            )

        try:
            totp = pyotp.TOTP(cast(str, totp_secret)).now()
        except Exception as e:
            raise AuthenticationError(f"Failed to generate TOTP: {e}")

        response = await self._client.post(
            _LOGIN_URL,
            headers=_base_headers(cast(str, api_key)),
            json={"clientcode": client_id, "password": pin, "totp": totp},
        )
        data = response.json()
        if not data.get("status") or "data" not in data:
            raise AuthenticationError(f"AngelOne login failed: {data.get('message', 'Unknown error')}")

        d = data["data"]
        self._session = SessionData(
            access_token=d["jwtToken"],
            refresh_token=d.get("refreshToken"),
            feed_token=d.get("feedToken"),
            expires_at=next_midnight_ist(),
        )
        logger.info(f"AngelOne login successful for {client_id}")

    async def _login_manual(self) -> None:
        """Create a session from user-provided JWT access token."""
        token = self._config.get("access_token")
        if not token:
            raise AuthenticationError(
                "AngelOne manual login requires 'access_token' in config (the jwtToken)."
            )
        self._session = SessionData(
            access_token=token,
            expires_at=next_midnight_ist(),
        )

    async def _refresh_auto(self) -> None:
        """Refresh JWT via renewToken endpoint; fallback to full login on failure."""
        if not self._session or not self._session.refresh_token:
            await self._login_auto()
            return

        api_key = str(self._config.get("api_key", ""))
        headers = {
            **_base_headers(api_key),
            "Authorization": f"Bearer {self._session.access_token}",
        }
        try:
            response = await self._client.post(
                _RENEW_URL,
                headers=headers,
                json={"refreshToken": self._session.refresh_token},
            )
            data = response.json()
            if not data.get("status") or "data" not in data:
                logger.warning("AngelOne token refresh failed, falling back to full login")
                await self._login_auto()
                return

            d = data["data"]
            self._session = SessionData(
                access_token=d["jwtToken"],
                refresh_token=d.get("refreshToken"),
                feed_token=d.get("feedToken"),
                expires_at=next_midnight_ist(),
            )
        except Exception as e:
            logger.warning(f"AngelOne token refresh error: {e}. Falling back to full login.")
            await self._login_auto()

    @property
    def headers(self) -> dict[str, str]:
        """Build authenticated headers required by AngelOne APIs."""
        if not self._session:
            raise AuthenticationError("Not authenticated. Call login() first.")
        return {
            **_base_headers(str(self._config.get("api_key", ""))),
            "Authorization": f"Bearer {self._session.access_token}",
        }
