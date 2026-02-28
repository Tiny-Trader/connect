import pytest

@pytest.mark.live
async def test_profile_returns_real_client_id(broker):
    profile = await broker.get_profile()
    assert profile.client_id
    assert "@" in profile.email

@pytest.mark.live
async def test_funds_are_non_negative(broker):
    fund = await broker.get_funds()
    assert fund.available >= 0
    assert fund.total >= 0

@pytest.mark.live
async def test_get_holdings(broker):
    holdings = await broker.get_holdings()
    assert isinstance(holdings, list)

@pytest.mark.live
async def test_get_positions(broker):
    positions = await broker.get_positions()
    assert isinstance(positions, list)


# ---------------------------------------------------------------------------
# Instrument master queries
# ---------------------------------------------------------------------------

@pytest.mark.live
async def test_get_expiries_returns_sorted_dates(broker):
    from tt_connect.instruments import Equity
    sbin = Equity(exchange="NSE", symbol="SBIN")
    expiries = await broker.get_expiries(sbin)

    assert len(expiries) > 0
    assert expiries == sorted(expiries)


@pytest.mark.live
async def test_get_futures_returns_future_objects(broker):
    from datetime import date
    from tt_connect.instruments import Equity, Future
    sbin = Equity(exchange="NSE", symbol="SBIN")
    futures = await broker.get_futures(sbin)

    assert len(futures) > 0
    assert all(isinstance(f, Future) for f in futures)
    assert all(f.symbol == "SBIN" for f in futures)
    assert all(isinstance(f.expiry, date) for f in futures)
    # Sorted ascending
    assert [f.expiry for f in futures] == sorted(f.expiry for f in futures)


@pytest.mark.live
async def test_get_options_all_expiries(broker):
    from tt_connect.instruments import Equity, Option
    sbin = Equity(exchange="NSE", symbol="SBIN")
    options = await broker.get_options(sbin)

    assert len(options) > 0
    assert all(isinstance(o, Option) for o in options)
    assert all(o.symbol == "SBIN" for o in options)
    assert all(o.option_type in ("CE", "PE") for o in options)


@pytest.mark.live
async def test_get_options_filtered_by_expiry(broker):
    from tt_connect.instruments import Equity
    sbin = Equity(exchange="NSE", symbol="SBIN")

    # Use the nearest expiry from get_expiries
    expiries = await broker.get_expiries(sbin)
    assert expiries, "SBIN should have at least one expiry"
    nearest = expiries[0]

    options = await broker.get_options(sbin, expiry=nearest)
    assert len(options) > 0
    assert all(o.expiry == nearest for o in options)
    # Should have both CE and PE
    types = {o.option_type for o in options}
    assert "CE" in types
    assert "PE" in types


@pytest.mark.live
async def test_get_options_has_ce_pe_pairs(broker):
    """Each strike should have exactly one CE and one PE for a given expiry."""
    from tt_connect.instruments import Equity
    sbin = Equity(exchange="NSE", symbol="SBIN")

    expiries = await broker.get_expiries(sbin)
    nearest = expiries[0]
    options = await broker.get_options(sbin, expiry=nearest)

    strikes = {o.strike for o in options}
    # Check a few strikes have both sides
    for strike in list(strikes)[:5]:
        at_strike = [o for o in options if o.strike == strike]
        ot_types = {o.option_type for o in at_strike}
        assert "CE" in ot_types and "PE" in ot_types
