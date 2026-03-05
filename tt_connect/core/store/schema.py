"""SQLite schema, versioning, and connection helpers for the instrument cache.

Schema versioning strategy
--------------------------
The DB is a pure cache — rebuilt daily from the broker's live instrument master.
There is no user data to preserve. When the schema changes, the right move is to
drop everything and recreate it clean, then let the normal staleness refresh
repopulate from the API.

Bump SCHEMA_VERSION whenever any CREATE TABLE statement changes. On the next
client init(), the version mismatch is detected, the old schema is discarded,
and a fresh one is written — all transparently, before any data access.
"""

import aiosqlite
from pathlib import Path

DB_DIR = Path("_cache")
"""Default directory for per-broker SQLite instrument databases."""

SCHEMA_VERSION = 2
"""Current schema revision. Bump this whenever any CREATE TABLE changes —
the next ``init_schema()`` call will drop and recreate all tables."""


def get_db_path(broker_id: str) -> Path:
    """Return the SQLite database file path for a broker.

    Path convention: ``_cache/{broker_id}_instruments.db``.
    """
    return DB_DIR / f"{broker_id}_instruments.db"


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DROP = """
DROP TABLE IF EXISTS broker_tokens;
DROP TABLE IF EXISTS equities;
DROP TABLE IF EXISTS futures;
DROP TABLE IF EXISTS options;
DROP TABLE IF EXISTS instruments;
DROP TABLE IF EXISTS _meta;
"""

_CREATE = """
CREATE TABLE _meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE instruments (
    id        INTEGER PRIMARY KEY,
    exchange  TEXT NOT NULL CHECK (exchange IN ('NSE','BSE','NFO','BFO','CDS','MCX')),
    symbol    TEXT NOT NULL,
    segment   TEXT NOT NULL,
    name      TEXT,
    lot_size  INTEGER,
    tick_size REAL
);

CREATE TABLE equities (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    isin          TEXT
);

CREATE TABLE futures (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_id INTEGER NOT NULL REFERENCES instruments(id),
    expiry        DATE NOT NULL
);

CREATE TABLE options (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_id INTEGER NOT NULL REFERENCES instruments(id),
    expiry        DATE NOT NULL,
    strike        REAL NOT NULL,
    option_type   TEXT NOT NULL CHECK (option_type IN ('CE', 'PE'))
);

CREATE TABLE broker_tokens (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    broker_id     TEXT NOT NULL,
    token         TEXT NOT NULL,
    broker_symbol TEXT NOT NULL,
    PRIMARY KEY (instrument_id, broker_id)
);

CREATE INDEX idx_instruments ON instruments(exchange, symbol);
CREATE INDEX idx_futures      ON futures(underlying_id, expiry);
CREATE INDEX idx_options      ON options(underlying_id, expiry, strike, option_type);
"""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

async def get_connection(broker_id: str) -> aiosqlite.Connection:
    """Create a WAL-enabled SQLite connection with foreign keys enforced."""
    path = get_db_path(broker_id)
    path.parent.mkdir(exist_ok=True)
    conn = await aiosqlite.connect(path)
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ---------------------------------------------------------------------------
# Schema lifecycle
# ---------------------------------------------------------------------------

async def init_schema(conn: aiosqlite.Connection) -> None:
    """Ensure the schema is current.

    On a fresh DB or after a version bump: drops all tables and recreates them.
    On an up-to-date DB: no-op.
    """
    stored = await _get_schema_version(conn)
    if stored == SCHEMA_VERSION:
        return

    await conn.executescript(_DROP)
    await conn.executescript(_CREATE)
    await conn.execute(
        "INSERT INTO _meta (key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    await conn.commit()


async def truncate_all(conn: aiosqlite.Connection) -> None:
    """Clear all instrument and metadata rows before a full data refresh.

    Preserves the schema and schema_version — only removes instrument data
    and the last_updated staleness marker.
    """
    for table in ("broker_tokens", "equities", "futures", "options", "instruments"):
        await conn.execute(f"DELETE FROM {table}")
    await conn.execute("DELETE FROM _meta WHERE key = 'last_updated'")
    await conn.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_schema_version(conn: aiosqlite.Connection) -> int | None:
    """Return the stored schema version, or None if the DB is uninitialised."""
    try:
        async with conn.execute(
            "SELECT value FROM _meta WHERE key = 'schema_version'"
        ) as cur:
            row = await cur.fetchone()
        return int(row[0]) if row else None
    except aiosqlite.OperationalError:
        return None  # _meta doesn't exist yet — fresh DB
