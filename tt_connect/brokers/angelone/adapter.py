"""AngelOne REST adapter implementation."""

from __future__ import annotations

from tt_connect.core.adapter.base import BrokerAdapter
from tt_connect.core.adapter.transformer import JsonDict
from tt_connect.brokers.angelone.auth import AngelOneAuth
from tt_connect.brokers.angelone.transformer import AngelOneTransformer
from tt_connect.brokers.angelone.capabilities import ANGELONE_CAPABILITIES
from tt_connect.brokers.angelone.parser import parse, ParsedInstruments
from tt_connect.core.adapter.capabilities import Capabilities
from tt_connect.core.models.config import validate_config
from tt_connect.core.exceptions import OrderNotFoundError
from tt_connect.core.adapter.ws import BrokerWebSocket

BASE_URL        = "https://apiconnect.angelbroking.com/rest/secure/angelbroking"
GTT_BASE_URL    = "https://apiconnect.angelone.in/rest/secure/angelbroking/gtt/v1"
HISTORICAL_URL  = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData"
INSTRUMENTS_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"


class AngelOneAdapter(BrokerAdapter, broker_id="angelone"):
    """Broker adapter for AngelOne SmartAPI endpoints."""

    def __init__(self, config: JsonDict):
        """Initialize auth and transformer for AngelOne."""
        validate_config("angelone", config)
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

    async def get_profile(self) -> JsonDict:
        """Fetch raw profile payload."""
        return await self._request("GET", f"{BASE_URL}/user/v1/getProfile",
                                   headers=self.auth.headers)

    async def get_funds(self) -> JsonDict:
        """Fetch raw RMS/funds payload."""
        return await self._request("GET", f"{BASE_URL}/user/v1/getRMS",
                                   headers=self.auth.headers)

    async def get_holdings(self) -> JsonDict:
        """Fetch raw holdings and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/portfolio/v1/getHolding",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_positions(self) -> JsonDict:
        """Fetch raw positions and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/order/v1/getPosition",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_orders(self) -> JsonDict:
        """Fetch raw order book and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/order/v1/getOrderBook",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_trades(self) -> JsonDict:
        """Fetch raw trade book and normalize null data to empty list."""
        raw = await self._request("GET", f"{BASE_URL}/order/v1/getTradeBook",
                                  headers=self.auth.headers)
        raw["data"] = raw.get("data") or []
        return raw

    async def get_order(self, order_id: str) -> JsonDict:
        """Fetch a single order by filtering the full order book.

        AngelOne SmartAPI has no single-order endpoint, so we fetch all
        orders and return the matching entry in the expected envelope.
        """
        raw = await self.get_orders()
        for order in raw["data"]:
            if order.get("orderid") == order_id:
                return {"data": order}
        raise OrderNotFoundError(f"Order {order_id} not found", broker_code="AB1013")

    async def place_order(self, params: JsonDict) -> JsonDict:
        """Place a new order using broker-native params."""
        return await self._request("POST", f"{BASE_URL}/order/v1/placeOrder",
                                   headers=self.auth.headers, json=params)

    async def modify_order(self, order_id: str, params: JsonDict) -> JsonDict:
        """Modify an order by id."""
        return await self._request("POST", f"{BASE_URL}/order/v1/modifyOrder",
                                   headers=self.auth.headers, json=params)

    async def cancel_order(self, order_id: str) -> JsonDict:
        """Cancel an order by id."""
        return await self._request("POST", f"{BASE_URL}/order/v1/cancelOrder",
                                   headers=self.auth.headers,
                                   json={"orderid": order_id, "variety": "NORMAL"})

    # --- GTT ---

    async def place_gtt(self, params: JsonDict) -> JsonDict:
        """Create a new GTT rule."""
        return await self._request("POST", f"{GTT_BASE_URL}/createRule",
                                   headers=self.auth.headers, json=params)

    async def modify_gtt(self, gtt_id: str, params: JsonDict) -> JsonDict:
        """Modify an existing GTT rule."""
        payload = {**params, "id": gtt_id}
        return await self._request("POST", f"{GTT_BASE_URL}/modifyRule",
                                   headers=self.auth.headers, json=payload)

    async def cancel_gtt(self, gtt_id: str) -> JsonDict:
        """Cancel a GTT rule (fetches symbol details first as required by API)."""
        details = await self._request("POST", f"{GTT_BASE_URL}/ruleDetails",
                                      headers=self.auth.headers, json={"id": gtt_id})
        d = details["data"]
        return await self._request("POST", f"{GTT_BASE_URL}/cancelRule",
                                   headers=self.auth.headers,
                                   json={"id": gtt_id,
                                         "symboltoken": d["symboltoken"],
                                         "exchange": d["exchange"]})

    async def get_gtt(self, gtt_id: str) -> JsonDict:
        """Fetch a single GTT rule by id."""
        return await self._request("POST", f"{GTT_BASE_URL}/ruleDetails",
                                   headers=self.auth.headers, json={"id": gtt_id})

    async def get_gtts(self) -> JsonDict:
        """Fetch all GTT rules (active and recent), paginating automatically."""
        page_size = 50
        all_rules: list[JsonDict] = []
        page = 1

        while True:
            raw = await self._request(
                "POST", f"{GTT_BASE_URL}/ruleList",
                headers=self.auth.headers,
                json={"status": ["NEW", "CANCELLED", "ACTIVE", "SENTTOEXCHANGE", "FORALL"],
                      "page": page, "count": page_size},
            )
            data = raw.get("data")
            if data is None:
                break
            if isinstance(data, dict):
                all_rules.append(data)
                break
            all_rules.extend(data)
            if len(data) < page_size:
                break
            page += 1

        raw["data"] = all_rules
        return raw

    # --- Historical ---

    async def get_historical(self, token: str, params: JsonDict) -> JsonDict:
        """Fetch historical OHLC candles for an instrument token."""
        raw = await self._request("POST", HISTORICAL_URL,
                                  headers=self.auth.headers, json=params)
        raw["data"] = raw.get("data") or []
        return raw

    # --- WebSocket ---

    def create_ws_client(self) -> BrokerWebSocket:
        """Create broker-specific WebSocket client."""
        from tt_connect.brokers.angelone.ws import AngelOneWebSocket
        return AngelOneWebSocket(self.auth)

    # --- Capabilities ---

    @property
    def capabilities(self) -> Capabilities:
        """Return AngelOne capabilities declaration."""
        return ANGELONE_CAPABILITIES

    # --- Internal ---

    def _is_error(self, raw: JsonDict, status_code: int) -> bool:
        """Identify transport or broker-level error envelopes."""
        return raw.get("status") is False or status_code >= 400
