from datetime import date, timedelta
from unittest.mock import AsyncMock

import aiosqlite
import pytest
import pytest_asyncio
from freezegun import freeze_time

from tt_connect.brokers.zerodha.parser import parse
from tt_connect.core.models.enums import OnStale
from tt_connect.core.store.schema import (
    SCHEMA_VERSION,
    _get_schema_version,
    init_schema,
    truncate_all,
)
from tt_connect.core.store.manager import InstrumentManager

async def _count(db, table: str) -> int:
    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
        row = await cur.fetchone()
        return row[0]

async def test_insert_counts(populated_db):
    assert await _count(populated_db, "instruments") == 12
    assert await _count(populated_db, "equities") == 5  # 2 indices (also in equities) + 3 eqs
    assert await _count(populated_db, "futures") == 3
    assert await _count(populated_db, "options") == 4
    assert await _count(populated_db, "broker_tokens") == 12

async def test_futures_fk_integrity(populated_db):
    async with populated_db.execute("""
        SELECT COUNT(*) FROM futures f
        LEFT JOIN instruments u ON u.id = f.underlying_id
        WHERE u.id IS NULL
    """) as c:
        orphans = (await c.fetchone())[0]
    assert orphans == 0

async def test_options_fk_integrity(populated_db):
    async with populated_db.execute("""
        SELECT COUNT(*) FROM options o
        LEFT JOIN instruments u ON u.id = o.underlying_id
        WHERE u.id IS NULL
    """) as c:
        orphans = (await c.fetchone())[0]
    assert orphans == 0

async def test_idempotent_insert(db, zerodha_csv):
    """Inserting the same CSV twice (after truncate) yields same counts."""
    manager = InstrumentManager(broker_id="zerodha", on_stale=OnStale.FAIL)
    manager._conn = db
    parsed = parse(zerodha_csv)
    await manager._insert(parsed)
    first_count = await _count(db, "instruments")

    await truncate_all(db)
    await manager._insert(parsed)
    second_count = await _count(db, "instruments")

    assert first_count == second_count
    assert first_count == 12

async def test_is_stale_behavior(db):
    manager = InstrumentManager(broker_id="zerodha")
    manager._conn = db
    
    # 1. No meta record -> stale
    assert await manager._is_stale() is True
    
    # 2. Today's meta record -> not stale
    await manager._set_last_updated()
    assert await manager._is_stale() is False
    
    # 3. Yesterday's meta record -> stale
    with freeze_time(date.today() + timedelta(days=1)):
        assert await manager._is_stale() is True

# ---------------------------------------------------------------------------
# Schema versioning
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def raw_conn():
    """Bare in-memory connection with no schema applied."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    await conn.close()


async def test_fresh_db_gets_current_version(raw_conn):
    await init_schema(raw_conn)
    assert await _get_schema_version(raw_conn) == SCHEMA_VERSION


async def test_init_schema_is_idempotent(raw_conn):
    await init_schema(raw_conn)
    await init_schema(raw_conn)  # second call should be a no-op
    assert await _get_schema_version(raw_conn) == SCHEMA_VERSION


async def test_schema_version_mismatch_triggers_recreation(raw_conn):
    """Simulates upgrading tt-connect with a new schema version."""
    # Set up DB with an old version number
    await raw_conn.executescript("""
        CREATE TABLE _meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE instruments (id INTEGER PRIMARY KEY, exchange TEXT, symbol TEXT,
            segment TEXT, name TEXT, lot_size INTEGER, tick_size REAL);
    """)
    await raw_conn.execute(
        "INSERT INTO _meta (key, value) VALUES ('schema_version', '0')"
    )
    await raw_conn.commit()

    # init_schema detects version 0 != SCHEMA_VERSION, drops and recreates
    await init_schema(raw_conn)

    assert await _get_schema_version(raw_conn) == SCHEMA_VERSION
    # New schema has options table with CHECK constraint
    async with raw_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='options'"
    ) as cur:
        assert await cur.fetchone() is not None


async def test_truncate_preserves_schema_version(db):
    """truncate_all clears instrument data but keeps schema_version intact."""
    await truncate_all(db)
    assert await _get_schema_version(db) == SCHEMA_VERSION


async def test_option_type_check_constraint(db):
    """DB rejects option_type values outside CE/PE."""
    # Insert a minimal instrument row to satisfy the FK
    cursor = await db.execute(
        "INSERT INTO instruments (exchange, symbol, segment, lot_size, tick_size)"
        " VALUES ('NSE', 'NIFTY', 'INDICES', 50, 0.05)"
    )
    iid = cursor.lastrowid
    await db.execute("INSERT INTO equities (instrument_id) VALUES (?)", (iid,))

    with pytest.raises(aiosqlite.IntegrityError):
        await db.execute(
            "INSERT INTO options (instrument_id, underlying_id, expiry, strike, option_type)"
            " VALUES (?, ?, '2025-01-30', 23000.0, 'XX')",
            (iid, iid),
        )


async def test_exchange_check_constraint(raw_conn):
    """DB rejects exchange values outside the Exchange enum set."""
    await init_schema(raw_conn)
    with pytest.raises(aiosqlite.IntegrityError):
        await raw_conn.execute(
            "INSERT INTO instruments (exchange, symbol, segment, lot_size, tick_size)"
            " VALUES ('INVALID', 'TEST', 'TEST', 1, 0.05)"
        )


async def test_ensure_fresh_calls_refresh_only_when_stale(db):
    manager = InstrumentManager(broker_id="zerodha")
    manager._conn = db
    
    fetch_mock = AsyncMock(return_value=parse("")) # Empty parsed result
    
    # First call: stale (no meta) -> should call refresh
    await manager.ensure_fresh(fetch_mock)
    assert fetch_mock.await_count == 1
    
    # Second call: not stale (just updated) -> should NOT call refresh
    await manager.ensure_fresh(fetch_mock)
    assert fetch_mock.await_count == 1
