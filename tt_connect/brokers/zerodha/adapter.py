"""Zerodha REST adapter implementation."""

from tt_connect.core.adapter.base import BrokerAdapter
from tt_connect.core.adapter.transformer import JsonDict
from tt_connect.brokers.zerodha.auth import ZerodhaAuth
from tt_connect.brokers.zerodha.transformer import ZerodhaTransformer
from tt_connect.brokers.zerodha.capabilities import ZERODHA_CAPABILITIES
from tt_connect.brokers.zerodha.parser import parse, ParsedInstruments
from tt_connect.core.adapter.capabilities import Capabilities
from tt_connect.core.models.config import validate_config
from tt_connect.core.exceptions import AuthenticationError, BrokerError
from tt_connect.core.adapter.ws import BrokerWebSocket

BASE_URL = "https://api.kite.trade"


class ZerodhaAdapter(BrokerAdapter, broker_id="zerodha"):
    """Broker adapter for Zerodha Kite Connect APIs."""

    def __init__(self, config: JsonDict):
        """Initialize auth and transformer for Zerodha."""
        validate_config("zerodha", config)
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

    # --- GTT ---

    async def place_gtt(self, params: JsonDict) -> JsonDict:
        """Create a new GTT trigger (form-encoded body)."""
        return await self._request("POST", f"{BASE_URL}/gtt/triggers",
                                   headers=self.auth.headers, data=params)

    async def modify_gtt(self, gtt_id: str, params: JsonDict) -> JsonDict:
        """Modify an existing GTT trigger (form-encoded body)."""
        return await self._request("PUT", f"{BASE_URL}/gtt/triggers/{gtt_id}",
                                   headers=self.auth.headers, data=params)

    async def cancel_gtt(self, gtt_id: str) -> JsonDict:
        """Delete a GTT trigger by id."""
        return await self._request("DELETE", f"{BASE_URL}/gtt/triggers/{gtt_id}",
                                   headers=self.auth.headers)

    async def get_gtt(self, gtt_id: str) -> JsonDict:
        """Fetch a single GTT trigger by id."""
        return await self._request("GET", f"{BASE_URL}/gtt/triggers/{gtt_id}",
                                   headers=self.auth.headers)

    async def get_gtts(self) -> JsonDict:
        """Fetch all GTT triggers."""
        return await self._request("GET", f"{BASE_URL}/gtt/triggers",
                                   headers=self.auth.headers)

    # --- Market Quotes ---

    async def get_quotes(self, symbols: list[str]) -> JsonDict:
        """Fetch full market quotes for a list of 'exchange:tradingsymbol' keys."""
        return await self._request(
            "GET", f"{BASE_URL}/quote",
            headers=self.auth.headers,
            params=[("i", sym) for sym in symbols],
        )

    # --- Historical ---

    async def get_historical(self, token: str, params: JsonDict) -> JsonDict:
        """Fetch historical OHLC candles for an instrument token."""
        interval = params["interval"]
        query = {k: v for k, v in params.items() if k != "interval"}
        raw = await self._request(
            "GET", f"{BASE_URL}/instruments/historical/{token}/{interval}",
            headers=self.auth.headers, params=query,
        )
        # Normalize: flatten candles out of the nested data dict
        data = raw.get("data")
        candles = data.get("candles") if isinstance(data, dict) else None
        if not isinstance(candles, list):
            raise BrokerError("Unexpected historical payload from Zerodha: missing data.candles")
        raw["data"] = candles
        return raw

    # --- WebSocket ---

    def create_ws_client(self) -> BrokerWebSocket:
        """Return a KiteTicker WebSocket client for live streaming."""
        from tt_connect.brokers.zerodha.ws import ZerodhaWebSocket
        api_key = str(self._config.get("api_key", "")).strip()
        access_token = str(self.auth.access_token or "").strip()

        missing: list[str] = []
        if not api_key:
            missing.append("api_key")
        if not access_token:
            missing.append("access_token")
        if missing:
            raise AuthenticationError(
                "Cannot create Zerodha WebSocket client. Missing: " + ", ".join(missing)
            )

        return ZerodhaWebSocket(api_key=api_key, access_token=access_token)

    # --- Capabilities ---

    @property
    def capabilities(self) -> Capabilities:
        """Return Zerodha capabilities declaration."""
        return ZERODHA_CAPABILITIES

    # --- Internal ---

    def _is_error(self, raw: JsonDict, status_code: int) -> bool:
        """Identify transport or broker-level error envelopes."""
        return raw.get("status") == "error" or status_code >= 400
