"""Broker configuration base class with auto-registration.

Broker-specific configs live in their own packages (e.g. brokers/zerodha/config.py)
and register themselves via ``__init_subclass__``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from tt_connect.core.models.enums import OnStale
from tt_connect.core.exceptions import ConfigurationError


class BrokerConfig(BaseModel):
    """Fields shared by all broker configs."""

    model_config = ConfigDict(extra="forbid")

    _registry: ClassVar[dict[str, type["BrokerConfig"]]] = {}

    on_stale: OnStale = OnStale.FAIL
    cache_session: bool = False

    def __init_subclass__(cls, broker_id: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if broker_id:
            BrokerConfig._registry[broker_id] = cls

    def to_dict(self) -> dict[str, Any]:
        """Return the config as a plain dict for internal adapter/auth consumption."""
        return self.model_dump()


def validate_config(broker_id: str, raw: dict[str, Any] | BrokerConfig) -> BrokerConfig:
    """Validate raw config dict for a broker, returning a typed model.

    Raises :exc:`ConfigurationError` with a human-readable message on failure.
    Already-validated ``BrokerConfig`` instances pass through unchanged.
    """
    model_cls = BrokerConfig._registry.get(broker_id)

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
