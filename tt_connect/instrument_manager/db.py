"""SQLite schema and helpers for the local instrument master cache."""

import aiosqlite
from pathlib import Path

DB_PATH = Path("_cache/instruments.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    id        INTEGER PRIMARY KEY,
    exchange  TEXT NOT NULL,
    symbol    TEXT NOT NULL,
    segment   TEXT NOT NULL,
    name      TEXT,
    lot_size  INTEGER,
    tick_size REAL
);

CREATE TABLE IF NOT EXISTS equities (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    isin          TEXT
);

CREATE TABLE IF NOT EXISTS futures (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_id INTEGER NOT NULL REFERENCES instruments(id),
    expiry        DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS options (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_id INTEGER NOT NULL REFERENCES instruments(id),
    expiry        DATE NOT NULL,
    strike        REAL NOT NULL,
    option_type   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS broker_tokens (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    broker_id     TEXT NOT NULL,
    token         TEXT NOT NULL,
    broker_symbol TEXT NOT NULL,
    PRIMARY KEY (instrument_id, broker_id)
);

CREATE TABLE IF NOT EXISTS _meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_instruments ON instruments(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_futures      ON futures(underlying_id, expiry);
CREATE INDEX IF NOT EXISTS idx_options      ON options(underlying_id, expiry, strike, option_type);
"""


async def get_connection() -> aiosqlite.Connection:
    """Create a WAL-enabled SQLite connection with foreign keys enforced."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    return conn


async def init_schema(conn: aiosqlite.Connection) -> None:
    """Apply schema and indexes if they do not already exist."""
    await conn.executescript(SCHEMA)
    await conn.commit()


async def truncate_all(conn: aiosqlite.Connection) -> None:
    """Clear all instrument and metadata tables before a full refresh."""
    for table in ("broker_tokens", "equities", "futures", "options", "instruments", "_meta"):
        await conn.execute(f"DELETE FROM {table}")
    await conn.commit()
