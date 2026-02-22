"""Base tick normalization contract."""

from typing import Any

from tt_connect.models import Tick
from tt_connect.instruments import Instrument


class TickNormalizer:
    """Convert raw broker tick payloads into canonical :class:`Tick` objects."""

    def normalize(self, raw: dict[str, Any], instrument: Instrument) -> Tick:
        """Normalize one broker tick payload for a specific canonical instrument."""
        raise NotImplementedError
