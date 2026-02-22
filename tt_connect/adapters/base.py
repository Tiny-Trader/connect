from __future__ import annotations

import asyncio
import logging
from abc import abstractmethod
from typing import ClassVar, Protocol

import httpx

from tt_connect.capabilities import Capabilities
from tt_connect.exceptions import TTConnectError, UnsupportedFeatureError

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.0  # seconds; doubled on each attempt


class BrokerTransformer(Protocol):
    """Transformer contract implemented by each broker adapter."""

    @staticmethod
    def parse_error(raw: dict) -> TTConnectError: ...
    @staticmethod
    def to_order_id(raw: dict) -> str: ...
    @staticmethod
    def to_close_position_params(pos_raw: dict, qty: int, side) -> dict: ...


class BrokerAdapter:
    """Base class for broker integrations.

    Concrete adapters own broker-specific auth, REST wiring, and normalization.
    This base provides adapter auto-registration and shared HTTP retry behavior.
    """

    _registry: ClassVar[dict[str, type[BrokerAdapter]]] = {}

    def __init_subclass__(cls, broker_id: str | None = None, **kwargs):
        """Auto-register adapter classes by `broker_id` for client lookup."""
        super().__init_subclass__(**kwargs)
        if broker_id:
            BrokerAdapter._registry[broker_id] = cls

    def __init__(self, config: dict):
        """Initialize adapter with config and a shared async HTTP client."""
        self._config = config
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    # --- Lifecycle ---

    @abstractmethod
    async def login(self) -> None: ...

    @abstractmethod
    async def refresh_session(self) -> None: ...

    @abstractmethod
    async def fetch_instruments(self): ...

    # --- REST ---

    @abstractmethod
    async def get_profile(self) -> dict: ...

    @abstractmethod
    async def get_funds(self) -> dict: ...

    @abstractmethod
    async def get_holdings(self) -> list[dict]: ...

    @abstractmethod
    async def get_positions(self) -> list[dict]: ...

    @abstractmethod
    async def place_order(self, params: dict) -> dict: ...

    @abstractmethod
    async def modify_order(self, order_id: str, params: dict) -> dict: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> dict: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> dict: ...

    @abstractmethod
    async def get_orders(self) -> list[dict]: ...

    @abstractmethod
    async def get_trades(self) -> dict: ...

    # --- WebSocket ---

    def create_ws_client(self):
        """Return a broker-specific BrokerWebSocket. Override in adapters that support streaming."""
        raise UnsupportedFeatureError(
            f"{self.__class__.__name__} does not support WebSocket streaming."
        )

    # --- Capabilities ---

    @property
    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    @property
    @abstractmethod
    def transformer(self) -> BrokerTransformer: ...

    # --- Internal HTTP ---

    @abstractmethod
    def _is_error(self, raw: dict, status_code: int) -> bool: ...

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        """Perform a broker API request with timeout and transient-error retries.

        Retry policy:
        - Retries on `httpx.TimeoutException`
        - Retries on HTTP 5xx responses
        - Does not retry broker-declared/business errors (`_is_error`)
        """
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(f"Request timed out ({attempt}/{_MAX_RETRIES}): {method} {url}")
                await asyncio.sleep(_RETRY_BACKOFF * (2 ** (attempt - 1)))
                continue

            try:
                raw = response.json()
            except Exception:
                logger.error(f"Failed to parse JSON. Status: {response.status_code}, body: {response.text[:200]}")
                raise

            # 5xx — transient server error, retry
            if response.status_code >= 500:
                last_exc = TTConnectError(f"Server error {response.status_code} from {url}")
                logger.warning(f"Server error {response.status_code} ({attempt}/{_MAX_RETRIES}): {method} {url}")
                await asyncio.sleep(_RETRY_BACKOFF * (2 ** (attempt - 1)))
                continue

            # 4xx or broker-level error — do not retry
            if self._is_error(raw, response.status_code):
                raise self.transformer.parse_error(raw)

            return raw

        raise TTConnectError(f"Request failed after {_MAX_RETRIES} attempts: {method} {url}") from last_exc
