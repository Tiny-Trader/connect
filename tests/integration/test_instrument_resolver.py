import pytest
from datetime import date
from tt_connect.core.store.resolver import InstrumentResolver, ResolvedInstrument
from tt_connect.core.models.instruments import Index, Equity, Future, Option
from tt_connect.core.models.enums import Exchange
from tt_connect.core.exceptions import InstrumentNotFoundError

async def test_resolve_index(populated_db):
    resolver = InstrumentResolver(populated_db, "zerodha")
    # NIFTY 50 in CSV is mapped to NIFTY canonical symbol
    resolved = await resolver.resolve(Index(exchange=Exchange.NSE, symbol="NIFTY"))
    assert resolved.token == "256265"
    assert isinstance(resolved, ResolvedInstrument)

    # SENSEX
    resolved = await resolver.resolve(Index(exchange=Exchange.BSE, symbol="SENSEX"))
    assert resolved.token == "256266"

async def test_resolve_equity(populated_db):
    resolver = InstrumentResolver(populated_db, "zerodha")
    resolved = await resolver.resolve(Equity(exchange=Exchange.NSE, symbol="RELIANCE"))
    assert resolved.token == "738561"
    assert resolved.exchange == "NSE"

    resolved = await resolver.resolve(Equity(exchange=Exchange.BSE, symbol="RELIANCE"))
    assert resolved.token == "1280642"

async def test_resolve_future(populated_db):
    resolver = InstrumentResolver(populated_db, "zerodha")
    # Future resolution uses underlying exchange (NSE), not NFO
    resolved = await resolver.resolve(Future(
        exchange=Exchange.NSE,
        symbol="NIFTY",
        expiry=date(2026, 2, 26)
    ))
    assert resolved.token == "1000001"
    assert resolved.exchange == "NFO"

    # BFO future
    resolved = await resolver.resolve(Future(
        exchange=Exchange.BSE,
        symbol="SENSEX",
        expiry=date(2026, 2, 26)
    ))
    assert resolved.token == "1000003"

async def test_resolve_option(populated_db):
    resolver = InstrumentResolver(populated_db, "zerodha")
    resolved = await resolver.resolve(Option(
        exchange=Exchange.NSE,
        symbol="NIFTY",
        expiry=date(2026, 2, 26),
        strike=23000.0,
        option_type="CE"
    ))
    assert resolved.token == "1000004"
    assert resolved.exchange == "NFO"

async def test_resolve_unknown_raises(populated_db):
    resolver = InstrumentResolver(populated_db, "zerodha")
    with pytest.raises(InstrumentNotFoundError):
        await resolver.resolve(Equity(exchange=Exchange.NSE, symbol="NONEXISTENT"))

async def test_resolve_caching(populated_db):
    resolver = InstrumentResolver(populated_db, "zerodha")
    inst = Equity(exchange=Exchange.NSE, symbol="SBIN")

    resolved1 = await resolver.resolve(inst)
    assert resolved1.token == "1280641"

    # Verify it's in cache
    assert inst in resolver._cache
    assert resolver._cache[inst].token == "1280641"

    # Second call should use cache
    resolved2 = await resolver.resolve(inst)
    assert resolved2 == resolved1
