from tt_connect.adapters.base import BrokerAdapter
from tt_connect.adapters.zerodha.auth import ZerodhaAuth
from tt_connect.adapters.zerodha.transformer import ZerodhaTransformer
from tt_connect.adapters.zerodha.capabilities import ZERODHA_CAPABILITIES
from tt_connect.adapters.zerodha.parser import parse, ParsedInstruments
from tt_connect.capabilities import Capabilities

BASE_URL = "https://api.kite.trade"


class ZerodhaAdapter(BrokerAdapter, broker_id="zerodha"):

    def __init__(self, config: dict):
        super().__init__(config)
        self.auth = ZerodhaAuth(config, self._client)
        self._transformer = ZerodhaTransformer()

    @property
    def transformer(self) -> ZerodhaTransformer:
        return self._transformer

    # --- Lifecycle ---

    async def login(self) -> None:
        await self.auth.login()

    async def refresh_session(self) -> None:
        await self.auth.refresh()

    async def fetch_instruments(self) -> ParsedInstruments:
        response = await self._client.get(f"{BASE_URL}/instruments")
        response.raise_for_status()
        return parse(response.text)

    # --- REST ---

    async def get_profile(self) -> dict:
        return await self._request("GET", f"{BASE_URL}/user/profile",
                                   headers=self.auth.headers)

    async def get_funds(self) -> dict:
        return await self._request("GET", f"{BASE_URL}/user/margins",
                                   headers=self.auth.headers)

    async def get_holdings(self) -> list[dict]:
        return await self._request("GET", f"{BASE_URL}/portfolio/holdings",
                                   headers=self.auth.headers)

    async def get_positions(self) -> list[dict]:
        raw = await self._request("GET", f"{BASE_URL}/portfolio/positions",
                                  headers=self.auth.headers)
        # Zerodha returns {"data": {"net": [...], "day": [...]}}
        # Expose only net (open) positions; skip flat rows (qty == 0).
        raw["data"] = [p for p in raw["data"]["net"] if p["quantity"] != 0]
        return raw

    async def get_trades(self) -> dict:
        return await self._request("GET", f"{BASE_URL}/trades",
                                   headers=self.auth.headers)

    async def place_order(self, params: dict) -> dict:
        return await self._request("POST", f"{BASE_URL}/orders/regular",
                                   headers=self.auth.headers, data=params)

    async def modify_order(self, order_id: str, params: dict) -> dict:
        return await self._request("PUT", f"{BASE_URL}/orders/regular/{order_id}",
                                   headers=self.auth.headers, data=params)

    async def cancel_order(self, order_id: str) -> dict:
        return await self._request("DELETE", f"{BASE_URL}/orders/regular/{order_id}",
                                   headers=self.auth.headers)

    async def get_order(self, order_id: str) -> dict:
        return await self._request("GET", f"{BASE_URL}/orders/{order_id}",
                                   headers=self.auth.headers)

    async def get_orders(self) -> list[dict]:
        return await self._request("GET", f"{BASE_URL}/orders",
                                   headers=self.auth.headers)

    # --- Capabilities ---

    @property
    def capabilities(self) -> Capabilities:
        return ZERODHA_CAPABILITIES

    # --- Internal ---

    def _is_error(self, raw: dict, status_code: int) -> bool:
        return raw.get("status") == "error" or status_code >= 400
