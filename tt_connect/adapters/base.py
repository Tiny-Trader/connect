from __future__ import annotations

import asyncio
import logging
import time
from abc import abstractmethod
from typing import Any, ClassVar, Protocol
from urllib.parse import urlparse

import httpx

from tt_connect.capabilities import Capabilities
from tt_connect.exceptions import TTConnectError, UnsupportedFeatureError
from tt_connect.models import Candle, Fund, GetHistoricalRequest, Gtt, Holding, ModifyGttRequest, ModifyOrderRequest, Order, PlaceGttRequest, PlaceOrderRequest, Position, Profile, Tick, Trade
from tt_connect.ws.client import BrokerWebSocket

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)


def _url_path(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return parsed.path or "/"
    return parsed.path or url
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.0  # seconds; doubled on each attempt
JsonDict = dict[str, Any]


class BrokerTransformer(Protocol):
    """Transformer contract implemented by each broker adapter."""

    @staticmethod
    def parse_error(raw: JsonDict) -> TTConnectError: ...
    @staticmethod
    def to_order_id(raw: JsonDict) -> str: ...
    @staticmethod
    def to_close_position_params(pos_raw: JsonDict, qty: int, side: Any) -> JsonDict: ...
    @staticmethod
    def to_order_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceOrderRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_modify_params(req: ModifyOrderRequest) -> JsonDict: ...
    @staticmethod
    def to_gtt_id(raw: JsonDict) -> str: ...
    @staticmethod
    def to_gtt_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceGttRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_modify_gtt_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: ModifyGttRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_gtt(raw: JsonDict) -> Gtt: ...
    @staticmethod
    def to_profile(raw: JsonDict) -> Profile: ...
    @staticmethod
    def to_fund(raw: JsonDict) -> Fund: ...
    @staticmethod
    def to_holding(raw: JsonDict) -> Holding: ...
    @staticmethod
    def to_position(raw: JsonDict) -> Position: ...
    @staticmethod
    def to_trade(raw: JsonDict) -> Trade: ...
    @staticmethod
    def to_order(raw: JsonDict, instrument: Any = None) -> Order: ...
    @staticmethod
    def to_historical_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: GetHistoricalRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_candles(rows: list[Any], instrument: Any) -> list[Candle]: ...
    @staticmethod
    def to_quote(raw: JsonDict, instrument: Any) -> Tick: ...


class BrokerAdapter:
    """Base class for broker integrations.

    Concrete adapters own broker-specific auth, REST wiring, and normalization.
    This base provides adapter auto-registration and shared HTTP retry behavior.
    """

    _registry: ClassVar[dict[str, type[BrokerAdapter]]] = {}
    _broker_id: ClassVar[str] = "unknown"

    def __init_subclass__(cls, broker_id: str | None = None, **kwargs: Any) -> None:
        """Auto-register adapter classes by `broker_id` for client lookup."""
        super().__init_subclass__(**kwargs)
        if broker_id:
            BrokerAdapter._registry[broker_id] = cls
            cls._broker_id = broker_id

    def __init__(self, config: JsonDict):
        """Initialize adapter with config and a shared async HTTP client."""
        self._config = config
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    # --- Lifecycle ---

    @abstractmethod
    async def login(self) -> None: ...

    @abstractmethod
    async def refresh_session(self) -> None: ...

    @abstractmethod
    async def fetch_instruments(self) -> Any: ...

    # --- REST ---

    @abstractmethod
    async def get_profile(self) -> JsonDict: ...

    @abstractmethod
    async def get_funds(self) -> JsonDict: ...

    @abstractmethod
    async def get_holdings(self) -> JsonDict: ...

    @abstractmethod
    async def get_positions(self) -> JsonDict: ...

    @abstractmethod
    async def place_order(self, params: JsonDict) -> JsonDict: ...

    @abstractmethod
    async def modify_order(self, order_id: str, params: JsonDict) -> JsonDict: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> JsonDict: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> JsonDict: ...

    @abstractmethod
    async def get_orders(self) -> JsonDict: ...

    @abstractmethod
    async def get_trades(self) -> JsonDict: ...

    # --- GTT ---

    async def place_gtt(self, params: JsonDict) -> JsonDict:
        """Place a GTT rule. Override in adapters that support GTT."""
        raise UnsupportedFeatureError(f"{self.__class__.__name__} does not support GTT.")

    async def modify_gtt(self, gtt_id: str, params: JsonDict) -> JsonDict:
        """Modify an existing GTT rule. Override in adapters that support GTT."""
        raise UnsupportedFeatureError(f"{self.__class__.__name__} does not support GTT.")

    async def cancel_gtt(self, gtt_id: str) -> JsonDict:
        """Cancel a GTT rule. Override in adapters that support GTT."""
        raise UnsupportedFeatureError(f"{self.__class__.__name__} does not support GTT.")

    async def get_gtt(self, gtt_id: str) -> JsonDict:
        """Fetch a single GTT rule. Override in adapters that support GTT."""
        raise UnsupportedFeatureError(f"{self.__class__.__name__} does not support GTT.")

    async def get_gtts(self) -> JsonDict:
        """Fetch all GTT rules. Override in adapters that support GTT."""
        raise UnsupportedFeatureError(f"{self.__class__.__name__} does not support GTT.")

    # --- Historical ---

    async def get_historical(self, token: str, params: JsonDict) -> JsonDict:
        """Fetch historical OHLC candles. Override in adapters that support historical data."""
        raise UnsupportedFeatureError(
            f"{self.__class__.__name__} does not support historical data."
        )

    async def get_quotes(self, symbols: list[str]) -> JsonDict:
        """Fetch market quotes by exchange:symbol keys. Override in adapters that support it."""
        raise UnsupportedFeatureError(
            f"{self.__class__.__name__} does not support REST market quotes."
        )

    # --- WebSocket ---

    def create_ws_client(self) -> BrokerWebSocket:
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
    def _is_error(self, raw: JsonDict, status_code: int) -> bool: ...

    async def _request(self, method: str, url: str, **kwargs: Any) -> JsonDict:
        """Perform a broker API request with timeout and transient-error retries.

        Retry policy:
        - Retries on `httpx.TimeoutException`
        - Retries on HTTP 5xx responses
        - Does not retry broker-declared/business errors (`_is_error`)
        """
        last_exc: Exception | None = None
        url_path = _url_path(url)
        for attempt in range(1, _MAX_RETRIES + 1):
            t0 = time.monotonic()
            logger.debug(
                f"Request start ({attempt}/{_MAX_RETRIES}): {method} {url_path}",
                extra={
                    "event": "request.start",
                    "broker": self._broker_id,
                    "method": method,
                    "url": url_path,
                    "attempt": attempt,
                },
            )
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                latency_ms = int((time.monotonic() - t0) * 1000)
                last_exc = exc
                logger.warning(
                    f"Request timed out ({attempt}/{_MAX_RETRIES}): {method} {url_path}",
                    extra={
                        "event": "request.timeout",
                        "broker": self._broker_id,
                        "method": method,
                        "url": url_path,
                        "attempt": attempt,
                        "max_retries": _MAX_RETRIES,
                        "latency_ms": latency_ms,
                    },
                )
                await asyncio.sleep(_RETRY_BACKOFF * (2 ** (attempt - 1)))
                continue

            try:
                raw = response.json()
            except Exception:
                logger.error(
                    "Failed to parse JSON from broker response",
                    extra={
                        "event": "request.json_error",
                        "broker": self._broker_id,
                        "method": method,
                        "url": url_path,
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type", ""),
                        "body_len": len(response.text),
                    },
                )
                raise
            if not isinstance(raw, dict):
                raise TTConnectError(f"Expected JSON object from {url_path}, got {type(raw).__name__}")

            # 5xx — transient server error, retry
            if response.status_code >= 500:
                last_exc = TTConnectError(f"Server error {response.status_code} from {url_path}")
                logger.warning(
                    f"Server error {response.status_code} ({attempt}/{_MAX_RETRIES}): {method} {url_path}",
                    extra={
                        "event": "request.server_error",
                        "broker": self._broker_id,
                        "method": method,
                        "url": url_path,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "max_retries": _MAX_RETRIES,
                    },
                )
                await asyncio.sleep(_RETRY_BACKOFF * (2 ** (attempt - 1)))
                continue

            # 4xx or broker-level error — do not retry
            if self._is_error(raw, response.status_code):
                raise self.transformer.parse_error(raw)

            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.debug(
                f"Request end ({attempt}/{_MAX_RETRIES}): {method} {url_path} → {response.status_code}",
                extra={
                    "event": "request.end",
                    "broker": self._broker_id,
                    "method": method,
                    "url": url_path,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "attempt": attempt,
                },
            )
            return raw

        raise TTConnectError(f"Request failed after {_MAX_RETRIES} attempts: {method} {url}") from last_exc
