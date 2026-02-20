from __future__ import annotations
from abc import abstractmethod
from typing import ClassVar, Protocol
import httpx
from tt_connect.capabilities import Capabilities
from tt_connect.exceptions import TTConnectError


class BrokerTransformer(Protocol):
    @staticmethod
    def parse_error(raw: dict) -> TTConnectError: ...


class BrokerAdapter:
    _registry: ClassVar[dict[str, type[BrokerAdapter]]] = {}

    def __init_subclass__(cls, broker_id: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if broker_id:
            BrokerAdapter._registry[broker_id] = cls

    def __init__(self, config: dict):
        self._config = config
        self._client = httpx.AsyncClient()

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
        response = await self._client.request(method, url, **kwargs)
        try:
            raw = response.json()
        except Exception:
            print(f"FAILED TO PARSE JSON. Status: {response.status_code}")
            print(f"RAW TEXT: {response.text}")
            raise
        if self._is_error(raw, response.status_code):
            raise self.transformer.parse_error(raw)
        return raw
