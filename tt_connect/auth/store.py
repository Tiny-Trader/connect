"""
Session persistence backends.

MemorySessionStore — in-process only, lost on restart.
FileSessionStore  — reads/writes _cache/{broker_id}_session.json.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from tt_connect.auth.base import BaseSessionStore, SessionData

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("_cache")


class MemorySessionStore(BaseSessionStore):
    """Non-persistent store; session lives only for the current process."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}

    def load(self, broker_id: str) -> SessionData | None:
        """Return in-memory session for a broker if present."""
        return self._sessions.get(broker_id)

    def save(self, broker_id: str, session: SessionData) -> None:
        """Store session in process memory."""
        self._sessions[broker_id] = session

    def clear(self, broker_id: str) -> None:
        """Remove in-memory session for a broker."""
        self._sessions.pop(broker_id, None)


class FileSessionStore(BaseSessionStore):
    """Persists sessions to _cache/{broker_id}_session.json."""

    def __init__(self, cache_dir: Path = _CACHE_DIR) -> None:
        self._cache_dir = cache_dir

    def _path(self, broker_id: str) -> Path:
        """Compute the JSON session cache path for a broker."""
        return self._cache_dir / f"{broker_id}_session.json"

    def load(self, broker_id: str) -> SessionData | None:
        """Load broker session from disk; return ``None`` on miss/parse failure."""
        path = self._path(broker_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            expires_at = None
            if data.get("expires_at"):
                expires_at = datetime.fromisoformat(data["expires_at"])
            obtained_at = datetime.fromisoformat(
                data.get("obtained_at", datetime.now(timezone.utc).isoformat())
            )
            return SessionData(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                feed_token=data.get("feed_token"),
                obtained_at=obtained_at,
                expires_at=expires_at,
            )
        except Exception as exc:
            logger.warning(f"[{broker_id}] Failed to load cached session: {exc}. Re-login required.")
            return None

    def save(self, broker_id: str, session: SessionData) -> None:
        """Persist broker session as JSON under `_cache/`."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(broker_id)
        data = {
            "broker": broker_id,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "feed_token": session.feed_token,
            "obtained_at": session.obtained_at.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
        path.write_text(json.dumps(data, indent=2))
        logger.debug(f"[{broker_id}] Session cached to {path}")

    def clear(self, broker_id: str) -> None:
        """Delete broker session JSON file if it exists."""
        path = self._path(broker_id)
        if path.exists():
            path.unlink()
            logger.debug(f"[{broker_id}] Cached session cleared")
