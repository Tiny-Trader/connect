"""Typed, validated configuration models for each supported broker.

Usage::

    from tt_connect import TTConnect, AngelOneConfig

    config = AngelOneConfig(
        api_key="SP7RmmCu",
        client_id="A2357374",
        pin="8985",
        totp_secret="EL7KI5...",
    )
    client = TTConnect("angelone", config)

Raw dicts are also accepted and validated at construction time::

    client = TTConnect("angelone", {
        "api_key": "SP7RmmCu",
        "client_id": "A2357374",
        "pin": "8985",
        "totp_secret": "EL7KI5...",
    })
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from tt_connect.enums import AuthMode, OnStale
from tt_connect.exceptions import ConfigurationError


class BrokerConfig(BaseModel):
    """Fields shared by all broker configs."""

    model_config = ConfigDict(extra="forbid")

    on_stale: OnStale = OnStale.FAIL
    cache_session: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return the config as a plain dict for internal adapter/auth consumption."""
        return self.model_dump()


class AngelOneConfig(BrokerConfig):
    """Validated configuration for AngelOne SmartAPI.

    AUTO mode (default) — library performs TOTP login automatically:
        api_key, client_id, pin, totp_secret  (all required)

    MANUAL mode — you supply an already-obtained JWT token:
        api_key, access_token  (both required)
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
    def _check_credentials(self) -> AngelOneConfig:
        if self.auth_mode == AuthMode.AUTO:
            missing = [f for f in ("client_id", "pin", "totp_secret") if not getattr(self, f)]
            if missing:
                raise ValueError(f"AngelOne AUTO mode requires: {', '.join(missing)}")
        else:
            if not self.access_token:
                raise ValueError("AngelOne MANUAL mode requires 'access_token'")
        return self


class ZerodhaConfig(BrokerConfig):
    """Validated configuration for Zerodha Kite Connect.

    Zerodha uses OAuth — obtain ``access_token`` via the Kite login URL
    and supply it here. Token expires at midnight IST each day.
    """

    api_key: str
    access_token: str


# ---------------------------------------------------------------------------
# Internal helper — called by each adapter __init__
# ---------------------------------------------------------------------------

_CONFIG_MODELS: dict[str, type[BrokerConfig]] = {
    "angelone": AngelOneConfig,
    "zerodha": ZerodhaConfig,
}


def validate_config(broker_id: str, raw: dict[str, Any] | BrokerConfig) -> BrokerConfig:
    """Validate raw config dict for a broker, returning a typed model.

    Raises :exc:`ConfigurationError` with a human-readable message on failure.
    Already-validated ``BrokerConfig`` instances pass through unchanged.
    """
    model_cls = _CONFIG_MODELS.get(broker_id)

    if isinstance(raw, BrokerConfig):
        if model_cls is not None and not isinstance(raw, model_cls):
            raise ConfigurationError(
                f"Config type mismatch for broker '{broker_id}': expected "
                f"{model_cls.__name__}, got {type(raw).__name__}."
            )
        return raw

    if model_cls is None:
        # Unknown broker — skip validation; let the adapter registry raise later
        return BrokerConfig.model_validate({})

    from pydantic import ValidationError

    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        lines = []
        for e in exc.errors():
            field = ".".join(str(loc) for loc in e["loc"]) if e["loc"] else "config"
            lines.append(f"  {field}: {e['msg']}")
        raise ConfigurationError(
            f"Invalid {broker_id} configuration:\n" + "\n".join(lines)
        ) from exc
