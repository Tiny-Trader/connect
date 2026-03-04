import aiosqlite
import pytest_asyncio
from tt_connect.core.store.schema import init_schema
from tt_connect.core.store.manager import InstrumentManager
from tt_connect.brokers.zerodha.parser import parse
from tt_connect.core.models.enums import OnStale

@pytest_asyncio.fixture
async def db():
    """Fresh in-memory SQLite DB with schema applied."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA foreign_keys = ON")
    await init_schema(conn)
    yield conn
    await conn.close()

@pytest_asyncio.fixture
async def populated_db(db, zerodha_csv):
    """DB with fixture CSV already parsed and inserted."""
    parsed = parse(zerodha_csv)
    manager = InstrumentManager(broker_id="zerodha", on_stale=OnStale.FAIL)
    manager._conn = db
    await manager._insert(parsed)
    yield db
