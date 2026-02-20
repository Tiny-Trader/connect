import httpx
import pyotp
import logging
import socket
from tt_connect.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

class AngelOneAuth:
    def __init__(self, config: dict, client: httpx.AsyncClient):
        self._config = config
        self._client = client
        self._jwt_token: str | None = None
        self._refresh_token: str | None = None
        self._feed_token: str | None = None
        
        # Header constants/defaults
        self._local_ip = self._get_local_ip()
        self._public_ip = "106.193.147.210" # Placeholder, SmartAPI often accepts static/placeholder
        self._mac_address = "00:00:00:00:00:00" # Placeholder

    async def login(self) -> None:
        """
        Automated login using client_id, pin, and totp_secret.
        """
        client_id = self._config.get("client_id")
        pin = self._config.get("pin")
        totp_secret = self._config.get("totp_secret")
        api_key = self._config.get("api_key")

        if not all([client_id, pin, totp_secret, api_key]):
            raise AuthenticationError(
                "AngelOne requires 'client_id', 'pin', 'totp_secret' and 'api_key' in config."
            )

        try:
            totp = pyotp.TOTP(totp_secret).now()
        except Exception as e:
            raise AuthenticationError(f"Failed to generate TOTP: {e}")

        payload = {
            "clientcode": client_id,
            "password": pin,
            "totp": totp
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": self._local_ip,
            "X-ClientPublicIP": self._public_ip,
            "X-MACAddress": self._mac_address,
            "X-PrivateKey": api_key,
        }

        try:
            response = await self._client.post(
                "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword",
                headers=headers,
                json=payload
            )
            data = response.json()
            
            if not data.get("status") or "data" not in data:
                message = data.get("message", "Unknown error")
                raise AuthenticationError(f"AngelOne login failed: {message}")

            login_data = data["data"]
            self._jwt_token = login_data["jwtToken"]
            self._refresh_token = login_data.get("refreshToken")
            self._feed_token = login_data.get("feedToken")
            
            logger.info(f"AngelOne login successful for {client_id}")

        except httpx.HTTPError as e:
            raise AuthenticationError(f"AngelOne connection error: {e}")
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"An unexpected error occurred during login: {e}")

    async def refresh(self) -> None:
        """
        Refresh the session using the refresh token.
        """
        if not self._refresh_token:
            await self.login()
            return

        api_key = self._config.get("api_key")
        
        payload = {
            "refreshToken": self._refresh_token
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": self._local_ip,
            "X-ClientPublicIP": self._public_ip,
            "X-MACAddress": self._mac_address,
            "X-PrivateKey": api_key,
            "Authorization": f"Bearer {self._jwt_token}"
        }

        try:
            response = await self._client.post(
                "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/renewToken",
                headers=headers,
                json=payload
            )
            data = response.json()
            
            if not data.get("status") or "data" not in data:
                logger.warning("Token refresh failed, attempting full login")
                await self.login()
                return

            login_data = data["data"]
            self._jwt_token = login_data["jwtToken"]
            self._refresh_token = login_data.get("refreshToken")
            self._feed_token = login_data.get("feedToken")

        except Exception as e:
            logger.warning(f"Token refresh failed: {e}. Attempting full login.")
            await self.login()

    @property
    def headers(self) -> dict:
        if not self._jwt_token:
            raise AuthenticationError("Not authenticated. Call login() first.")
            
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": self._local_ip,
            "X-ClientPublicIP": self._public_ip,
            "X-MACAddress": self._mac_address,
            "X-PrivateKey": self._config.get("api_key", ""),
            "Authorization": f"Bearer {self._jwt_token}"
        }

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
