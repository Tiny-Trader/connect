"""
Auth base classes for tt-connect.

Every broker's auth class extends BaseAuth and overrides:
  - _broker_id       — used for session file naming
  - _default_mode    — mode used when config has no "auth_mode" key
  - _supported_modes — set of modes this broker actually supports
  - _login_manual()  — read token from config, populate self._session
  - _login_auto()    — perform full TOTP/OAuth flow, populate self._session
  - _refresh_auto()  — renew token without full re-login (if supported)
  - headers property — return the HTTP headers dict for API calls
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tt_connect.enums import AuthMode
from tt_connect.exceptions import UnsupportedFeatureError

logger = logging.getLogger(__name__)

_IST = timezone(timedelta(hours=5, minutes=30))


def next_midnight_ist() -> datetime:
    """Return the next midnight IST as a timezone-aware UTC datetime.

    All major Indian brokers expire tokens at midnight IST.
    """
    now_ist = datetime.now(_IST)
    expiry_ist = (now_ist + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return expiry_ist.astimezone(timezone.utc)


@dataclass
class SessionData:
    """Holds the live auth state for a broker session."""
    access_token: str
    refresh_token: str | None = None
    feed_token: str | None = None
    obtained_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at


class BaseSessionStore:
    """Abstract session persistence layer."""

    def load(self, broker_id: str) -> SessionData | None:
        """Return cached session data for a broker, or ``None`` if absent."""
        raise NotImplementedError

    def save(self, broker_id: str, session: SessionData) -> None:
        """Persist session data for a broker."""
        raise NotImplementedError

    def clear(self, broker_id: str) -> None:
        """Delete cached session data for a broker."""
        raise NotImplementedError


class BaseAuth:
    """
    Base class for all broker auth implementations.

    Subclasses declare which modes they support via class variables and
    implement the mode-specific login/refresh logic.

    Config keys consumed here (broker-agnostic):
      auth_mode     — "manual" | "auto"  (default: _default_mode)
      cache_session — bool               (default: False)
    """

    _broker_id: str = "unknown"
    _default_mode: AuthMode = AuthMode.MANUAL
    _supported_modes: frozenset[AuthMode] = frozenset({AuthMode.MANUAL})

    def __init__(self, config: dict[str, Any], client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client
        self._session: SessionData | None = None

        # Resolve and validate auth mode
        mode_raw = config.get("auth_mode", self._default_mode.value)
        try:
            self._mode = AuthMode(mode_raw)
        except ValueError:
            raise UnsupportedFeatureError(
                f"Unknown auth_mode: '{mode_raw}'. Valid values: 'manual', 'auto'."
            )

        if self._mode not in self._supported_modes:
            supported = ", ".join(sorted(m.value for m in self._supported_modes))
            raise UnsupportedFeatureError(
                f"{self._broker_id} does not support auth_mode='{self._mode}'. "
                f"Supported: {supported}"
            )

        # Session store — opt-in file persistence
        from tt_connect.auth.store import FileSessionStore, MemorySessionStore
        self._store: BaseSessionStore = (
            FileSessionStore() if config.get("cache_session") else MemorySessionStore()
        )

    async def login(self) -> None:
        """Authenticate using configured mode, preferring unexpired cache."""
        # Check cache first — avoids a network round-trip on every init
        cached = self._store.load(self._broker_id)
        if cached and not cached.is_expired():
            logger.debug(f"[{self._broker_id}] Using cached session (expires {cached.expires_at})")
            self._session = cached
            return

        if self._mode == AuthMode.MANUAL:
            await self._login_manual()
        else:
            await self._login_auto()

        if self._session:
            self._store.save(self._broker_id, self._session)

    async def refresh(self) -> None:
        """Refresh auth session according to mode semantics."""
        if self._mode == AuthMode.AUTO:
            await self._refresh_auto()
        else:
            # Manual: force re-read from config — user may have updated access_token
            await self._login_manual()
            if self._session:
                self._store.save(self._broker_id, self._session)

    # --- Subclass hooks ---

    async def _login_manual(self) -> None:
        """Manual login hook; subclasses should read tokens from config."""
        raise NotImplementedError

    async def _login_auto(self) -> None:
        """Automated login hook; default raises if broker does not support it."""
        raise UnsupportedFeatureError(
            f"{self._broker_id} does not support automated login."
        )

    async def _refresh_auto(self) -> None:
        """Automated token refresh hook; default raises if unsupported."""
        raise UnsupportedFeatureError(
            f"{self._broker_id} does not support automated token refresh."
        )

    @property
    @abstractmethod
    def headers(self) -> dict[str, str]:
        """Return auth headers required by broker API requests."""
        raise NotImplementedError

    # --- Convenience ---

    @property
    def access_token(self) -> str | None:
        """Current access token if logged in, otherwise ``None``."""
        return self._session.access_token if self._session else None
