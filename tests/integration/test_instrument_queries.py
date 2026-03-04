"""Integration tests for InstrumentManager query methods using real SQLite."""

from __future__ import annotations

from datetime import date

from tt_connect.core.models.enums import OnStale
from tt_connect.core.store.manager import InstrumentManager
from tt_connect.core.models.instruments import Equity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manager(db) -> InstrumentManager:
    m = InstrumentManager(broker_id="zerodha", on_stale=OnStale.FAIL)
    m._conn = db
    return m


# ---------------------------------------------------------------------------
# get_futures
# ---------------------------------------------------------------------------

async def test_get_futures_returns_all_expiries(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    futures = await mgr.get_futures(reliance)

    assert len(futures) > 0
    assert all(f.symbol == "RELIANCE" for f in futures)
    assert all(str(f.exchange) == "NSE" for f in futures)
    # Results should be sorted ascending by expiry
    expiries = [f.expiry for f in futures]
    assert expiries == sorted(expiries)


async def test_get_futures_sorted_ascending(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    futures = await mgr.get_futures(reliance)
    expiries = [f.expiry for f in futures]
    assert expiries == sorted(expiries)


async def test_get_futures_unknown_underlying_returns_empty(populated_db):
    mgr = _manager(populated_db)
    unknown = Equity(exchange="NSE", symbol="DOESNOTEXIST")
    futures = await mgr.get_futures(unknown)
    assert futures == []


async def test_get_futures_returns_future_objects(populated_db):
    from tt_connect.core.models.instruments import Future
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    futures = await mgr.get_futures(reliance)
    assert all(isinstance(f, Future) for f in futures)


# ---------------------------------------------------------------------------
# get_options
# ---------------------------------------------------------------------------

async def test_get_options_no_filter_returns_all(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    options = await mgr.get_options(reliance)

    assert len(options) > 0
    assert all(o.symbol == "RELIANCE" for o in options)


async def test_get_options_expiry_filter(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")

    all_opts = await mgr.get_options(reliance)
    assert all_opts, "need at least one option in fixture"

    chosen_expiry = all_opts[0].expiry
    filtered = await mgr.get_options(reliance, expiry=chosen_expiry)

    assert all(o.expiry == chosen_expiry for o in filtered)
    assert len(filtered) <= len(all_opts)


async def test_get_options_expiry_filter_no_match(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    far_future = date(2099, 1, 1)
    options = await mgr.get_options(reliance, expiry=far_future)
    assert options == []


async def test_get_options_sorted(populated_db):
    from tt_connect.core.models.instruments import Option
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    options = await mgr.get_options(reliance)
    assert all(isinstance(o, Option) for o in options)
    # Verify sort order: expiry asc, then strike asc
    for a, b in zip(options, options[1:]):
        assert (a.expiry, a.strike) <= (b.expiry, b.strike)


async def test_get_options_unknown_underlying_returns_empty(populated_db):
    mgr = _manager(populated_db)
    unknown = Equity(exchange="NSE", symbol="DOESNOTEXIST")
    assert await mgr.get_options(unknown) == []


# ---------------------------------------------------------------------------
# get_expiries
# ---------------------------------------------------------------------------

async def test_get_expiries_covers_futures_and_options(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")

    expiries = await mgr.get_expiries(reliance)
    futures_expiries = {f.expiry for f in await mgr.get_futures(reliance)}
    options_expiries = {o.expiry for o in await mgr.get_options(reliance)}

    assert set(expiries) >= futures_expiries
    assert set(expiries) >= options_expiries


async def test_get_expiries_sorted_ascending(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    expiries = await mgr.get_expiries(reliance)
    assert expiries == sorted(expiries)


async def test_get_expiries_no_duplicates(populated_db):
    mgr = _manager(populated_db)
    reliance = Equity(exchange="NSE", symbol="RELIANCE")
    expiries = await mgr.get_expiries(reliance)
    assert len(expiries) == len(set(expiries))


async def test_get_expiries_unknown_underlying_returns_empty(populated_db):
    mgr = _manager(populated_db)
    unknown = Equity(exchange="NSE", symbol="DOESNOTEXIST")
    assert await mgr.get_expiries(unknown) == []


# ---------------------------------------------------------------------------
# search_instruments
# ---------------------------------------------------------------------------

async def test_search_instruments_returns_matches(populated_db):
    mgr = _manager(populated_db)
    results = await mgr.search_instruments("REL")
    symbols = [r.symbol for r in results]
    assert "RELIANCE" in symbols
    assert all(isinstance(r, Equity) for r in results)


async def test_search_instruments_case_insensitive(populated_db):
    mgr = _manager(populated_db)
    upper = await mgr.search_instruments("REL")
    lower = await mgr.search_instruments("rel")
    assert upper == lower


async def test_search_instruments_exchange_filter(populated_db):
    mgr = _manager(populated_db)
    results = await mgr.search_instruments("RELIANCE", exchange="NSE")
    assert all(str(r.exchange) == "NSE" for r in results)
    assert len(results) >= 1


async def test_search_instruments_no_match_returns_empty(populated_db):
    mgr = _manager(populated_db)
    results = await mgr.search_instruments("DOESNOTEXISTXYZ")
    assert results == []
