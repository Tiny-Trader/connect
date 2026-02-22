"""Zerodha REST adapter implementation."""

from tt_connect.adapters.base import BrokerAdapter
from tt_connect.adapters.base import JsonDict
from tt_connect.adapters.zerodha.auth import ZerodhaAuth
from tt_connect.adapters.zerodha.transformer import ZerodhaTransformer
from tt_connect.adapters.zerodha.capabilities import ZERODHA_CAPABILITIES
from tt_connect.adapters.zerodha.parser import parse, ParsedInstruments
from tt_connect.capabilities import Capabilities

BASE_URL = "https://api.kite.trade"


class ZerodhaAdapter(BrokerAdapter, broker_id="zerodha"):
    """Broker adapter for Zerodha Kite Connect APIs."""

    def __init__(self, config: JsonDict):
        """Initialize auth and transformer for Zerodha."""
        super().__init__(config)
        self.auth = ZerodhaAuth(config, self._client)
        self._transformer = ZerodhaTransformer()

    @property
    def transformer(self) -> ZerodhaTransformer:
        """Return Zerodha response/request transformer."""
        return self._transformer

    # --- Lifecycle ---

    async def login(self) -> None:
        """Authenticate using configured auth mode."""
        await self.auth.login()

    async def refresh_session(self) -> None:
        """Refresh current auth session."""
        await self.auth.refresh()

    async def fetch_instruments(self) -> ParsedInstruments:
        """Download and parse Zerodha instrument CSV dump."""
        response = await self._client.get(f"{BASE_URL}/instruments")
        response.raise_for_status()
        return parse(response.text)

    # --- REST ---

    async def get_profile(self) -> JsonDict:
        """Fetch raw profile payload from Zerodha."""
        return await self._request("GET", f"{BASE_URL}/user/profile",
                                   headers=self.auth.headers)

    async def get_funds(self) -> JsonDict:
        """Fetch raw funds/margins payload from Zerodha."""
        return await self._request("GET", f"{BASE_URL}/user/margins",
                                   headers=self.auth.headers)

    async def get_holdings(self) -> JsonDict:
        """Fetch raw holdings payload from Zerodha."""
        return await self._request("GET", f"{BASE_URL}/portfolio/holdings",
                                   headers=self.auth.headers)

    async def get_positions(self) -> JsonDict:
        """Fetch raw net positions and drop flat rows."""
        raw = await self._request("GET", f"{BASE_URL}/portfolio/positions",
                                  headers=self.auth.headers)
        # Zerodha returns {"data": {"net": [...], "day": [...]}}
        # Expose only net (open) positions; skip flat rows (qty == 0).
        raw["data"] = [p for p in raw["data"]["net"] if p["quantity"] != 0]
        return raw

    async def get_trades(self) -> JsonDict:
        """Fetch raw trade-book payload."""
        return await self._request("GET", f"{BASE_URL}/trades",
                                   headers=self.auth.headers)

    async def place_order(self, params: JsonDict) -> JsonDict:
        """Place a new order using broker-native params."""
        return await self._request("POST", f"{BASE_URL}/orders/regular",
                                   headers=self.auth.headers, data=params)

    async def modify_order(self, order_id: str, params: JsonDict) -> JsonDict:
        """Modify an existing order by id."""
        return await self._request("PUT", f"{BASE_URL}/orders/regular/{order_id}",
                                   headers=self.auth.headers, data=params)

    async def cancel_order(self, order_id: str) -> JsonDict:
        """Cancel an order by id."""
        return await self._request("DELETE", f"{BASE_URL}/orders/regular/{order_id}",
                                   headers=self.auth.headers)

    async def get_order(self, order_id: str) -> JsonDict:
        """Fetch one order by id."""
        return await self._request("GET", f"{BASE_URL}/orders/{order_id}",
                                   headers=self.auth.headers)

    async def get_orders(self) -> JsonDict:
        """Fetch complete order book."""
        return await self._request("GET", f"{BASE_URL}/orders",
                                   headers=self.auth.headers)

    # --- Capabilities ---

    @property
    def capabilities(self) -> Capabilities:
        """Return Zerodha capabilities declaration."""
        return ZERODHA_CAPABILITIES

    # --- Internal ---

    def _is_error(self, raw: JsonDict, status_code: int) -> bool:
        """Identify transport or broker-level error envelopes."""
        return raw.get("status") == "error" or status_code >= 400
