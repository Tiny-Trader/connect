"""IST timezone constant and Pydantic-compatible annotated type.

All datetime fields in tt-connect models are IST-aware.  Import ``IST`` when
constructing datetimes and ``ISTDatetime`` when annotating Pydantic fields:

    from tt_connect.core.timezone import IST, ISTDatetime

    dt = datetime(2024, 1, 1, 9, 15, tzinfo=IST)

The ``ISTDatetime`` validator:
- Accepts naive datetimes and assumes IST (the natural default for this library).
- Accepts any timezone-aware datetime and normalises it to IST.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import BeforeValidator

#: Indian Standard Time — fixed offset UTC+5:30 (no DST).
IST = timezone(timedelta(hours=5, minutes=30))


def _to_ist(v: object) -> datetime:
    if not isinstance(v, datetime):
        raise ValueError(f"Expected datetime, got {type(v).__name__}")
    if v.tzinfo is None:
        return v.replace(tzinfo=IST)  # naive → assumed IST
    return v.astimezone(IST)


#: Annotated datetime type for Pydantic models.  Normalises to IST; rejects naive.
ISTDatetime = Annotated[datetime, BeforeValidator(_to_ist)]
