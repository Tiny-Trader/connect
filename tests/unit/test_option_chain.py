"""Unit tests for OptionChain helper methods — no DB required."""

from __future__ import annotations

from datetime import date

import pytest

from tt_connect.core.models.enums import Exchange, OptionType
from tt_connect.core.models.instruments import Equity, Option, OptionChain, OptionChainEntry

_EXPIRY = date(2026, 2, 26)
_UNDERLYING = Equity(exchange=Exchange.NSE, symbol="NIFTY")


def _opt(strike: float, option_type: str) -> Option:
    return Option(
        exchange=Exchange.NSE,
        symbol="NIFTY",
        expiry=_EXPIRY,
        strike=strike,
        option_type=OptionType(option_type),
    )


def _entry(strike: float, *, ce: bool = True, pe: bool = True) -> OptionChainEntry:
    return OptionChainEntry(
        strike=strike,
        ce=_opt(strike, "CE") if ce else None,
        pe=_opt(strike, "PE") if pe else None,
    )


def _chain(strikes: list[float]) -> OptionChain:
    return OptionChain(
        underlying=_UNDERLYING,
        expiry=_EXPIRY,
        entries=[_entry(s) for s in strikes],
    )


def test_atm_returns_closest_strike():
    chain = _chain([22000, 22500, 23000, 23500, 24000])
    assert chain.atm(22600).strike == 22500


def test_atm_exact_match():
    chain = _chain([22000, 22500, 23000])
    assert chain.atm(23000).strike == 23000


def test_atm_empty_chain_raises_clear_error():
    chain = _chain([])
    with pytest.raises(ValueError, match="no option entries available"):
        chain.atm(23000)


def test_strikes_around_normal():
    chain = _chain([22000, 22500, 23000, 23500, 24000])
    result = chain.strikes_around(23000, 3)
    assert [e.strike for e in result] == [22500, 23000, 23500]


def test_strikes_around_near_upper_edge():
    chain = _chain([22000, 22500, 23000, 23500, 24000])
    result = chain.strikes_around(24000, 3)
    assert [e.strike for e in result] == [23000, 23500, 24000]


def test_strikes_around_near_lower_edge():
    chain = _chain([22000, 22500, 23000, 23500, 24000])
    result = chain.strikes_around(22000, 3)
    assert [e.strike for e in result] == [22000, 22500, 23000]
