"""Validated configuration for AngelOne SmartAPI."""

from pydantic import model_validator

from tt_connect.core.models.config import BrokerConfig
from tt_connect.core.models.enums import AuthMode


class AngelOneConfig(BrokerConfig, broker_id="angelone"):
    """Validated configuration for AngelOne SmartAPI.

    AUTO mode (default) — library performs TOTP login automatically:
        api_key, client_id, pin, totp_secret  (all required)

    MANUAL mode — you supply an already-obtained JWT token:
        api_key, access_token  (both required)

    Note:
        Validators raise ``ValueError`` (Pydantic convention). The public
        entry point ``validate_config()`` catches all ``ValidationError``s
        and wraps them into a single ``ConfigurationError``.
    """

    auth_mode: AuthMode = AuthMode.AUTO
    api_key: str

    # AUTO-mode fields
    client_id: str | None = None
    pin: str | None = None
    totp_secret: str | None = None

    # MANUAL-mode field
    access_token: str | None = None

    @model_validator(mode="after")
    def _check_credentials(self) -> "AngelOneConfig":
        if self.auth_mode == AuthMode.AUTO:
            missing = [f for f in ("client_id", "pin", "totp_secret") if not getattr(self, f)]
            if missing:
                raise ValueError(f"AngelOne AUTO mode requires: {', '.join(missing)}")
        else:
            if not self.access_token:
                raise ValueError("AngelOne MANUAL mode requires 'access_token'")
        return self

