"""AngelOne REST adapter implementation."""

from __future__ import annotations

from tt_connect.adapters.base import BrokerAdapter
from tt_connect.adapters.angelone.auth import AngelOneAuth
from tt_connect.adapters.angelone.transformer import AngelOneTransformer
from tt_connect.adapters.angelone.capabilities import ANGELONE_CAPABILITIES
from tt_connect.adapters.angelone.parser import parse, ParsedInstruments
from tt_connect.capabilities import Capabilities
from tt_connect.exceptions import UnsupportedFeatureError

BASE_URL = "https://apiconnect.angelbroking.com/rest/secure/angelbroking"
INSTRUMENTS_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"


class AngelOneAdapter(BrokerAdapter, broker_id="angelone"):
    """Broker adapter for AngelOne SmartAPI endpoints."""

    def __init__(self, config: dict):
        """Initialize auth and transformer for AngelOne."""
        super().__init__(config)
        self.auth = AngelOneAuth(config, self._client)
        self._transformer = AngelOneTransformer()

    @property
    def transformer(self) -> AngelOneTransformer:
        """Return AngelOne request/response transformer."""
        return self._transformer

    # --- Lifecycle ---

    async def login(self) -> None:
        """Authenticate using configured auth mode."""
        await self.auth.login()

    async def refresh_session(self) -> None:
        """Refresh current auth session."""
        await self.auth.refresh()

    async def fetch_instruments(self) -> ParsedInstruments:
        """Download and parse AngelOne instrument master JSON."""
        response = await self._client.get(INSTRUMENTS_URL)
        response.raise_for_status()
        return parse(response.json())

    # --- REST ---

    async def get_profile(self) -> dict:
        """Fetch raw profile payload."""
        return await self._request("GET", f"{BASE_URL}/user/v1/getProfile",
                                   headers=self.auth.headers)

    async def get_funds(self) -> dict:
        """Fetch raw RMS/funds payload."""
        return await self._request("GET", f"{BASE_URL}/user/v1/getRMS",
                                   headers=self.auth.headers)

    async def get_holdings(self) -> list[dict]:
        """Fetch raw holdings and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/portfolio/v1/getHolding",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_positions(self) -> list[dict]:
        """Fetch raw positions and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/order/v1/getPosition",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_orders(self) -> list[dict]:
        """Fetch raw order book and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/order/v1/getOrderBook",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_trades(self) -> dict:
        """Fetch raw trade book and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/order/v1/getTradeBook",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_order(self, order_id: str) -> dict:
        """Single-order endpoint is unavailable for AngelOne."""
        raise UnsupportedFeatureError(
            "AngelOne does not support fetching a single order by ID. "
            "Use get_orders() and filter by order_id."
        )

    async def place_order(self, params: dict) -> dict:
        """Place a new order using broker-native params."""
        return await self._request("POST", f"{BASE_URL}/order/v1/placeOrder",
                                   headers=self.auth.headers, json=params)

    async def modify_order(self, order_id: str, params: dict) -> dict:
        """Modify an order by id."""
        return await self._request("POST", f"{BASE_URL}/order/v1/modifyOrder",
                                   headers=self.auth.headers, json=params)

    async def cancel_order(self, order_id: str) -> dict:
        """Cancel an order by id."""
        return await self._request("POST", f"{BASE_URL}/order/v1/cancelOrder",
                                   headers=self.auth.headers,
                                   json={"orderid": order_id, "variety": "NORMAL"})

    # --- WebSocket ---

    def create_ws_client(self):
        """Create broker-specific WebSocket client."""
        from tt_connect.ws.angelone import AngelOneWebSocket
        return AngelOneWebSocket(self.auth)

    # --- Capabilities ---

    @property
    def capabilities(self) -> Capabilities:
        """Return AngelOne capabilities declaration."""
        return ANGELONE_CAPABILITIES

    # --- Internal ---

    def _is_error(self, raw: dict, status_code: int) -> bool:
        """Identify transport or broker-level error envelopes."""
        return raw.get("status") is False or status_code >= 400
