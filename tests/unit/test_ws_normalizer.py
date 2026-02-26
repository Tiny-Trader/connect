"""Unit tests for ws/normalizer.py — TickNormalizer base class."""

from __future__ import annotations

import pytest

from tt_connect.instruments import Equity
from tt_connect.ws.normalizer import TickNormalizer


def test_normalize_raises_not_implemented():
    normalizer = TickNormalizer()
    instr = Equity(exchange="NSE", symbol="RELIANCE")

    with pytest.raises(NotImplementedError):
        normalizer.normalize({}, instr)
