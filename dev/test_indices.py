"""
Quick smoke test for:
  1. Parser — reads actual Zerodha CSV, extracts indices
  2. DB schema — creates instruments.db, verifies all tables
  3. Insert — inserts parsed indices into DB
  4. Query — verifies canonical vs broker symbol separation
  5. Resolver — resolves Index objects to broker tokens
"""

import asyncio
import os
from pathlib import Path

# Point _cache at a temp location for this test
os.environ["TT_CACHE_DIR"] = "/tmp/tt_test_cache"

from tt_connect.adapters.zerodha.parser import parse, INDEX_NAME_MAP
from tt_connect.instrument_manager.db import get_connection, init_schema, truncate_all
from tt_connect.instrument_manager.manager import InstrumentManager
from tt_connect.instrument_manager.resolver import InstrumentResolver
from tt_connect.instruments import Index
from tt_connect.enums import Exchange, OnStale

CSV_PATH = Path("/Users/apurv/Desktop/algo-trading/master-instruments/data/zerodha.csv")
BROKER_ID = "zerodha"


# ---------------------------------------------------------------------------
# 1. Parser
# ---------------------------------------------------------------------------
print("=" * 60)
print("1. PARSER")
print("=" * 60)

raw_csv = CSV_PATH.read_text()
parsed = parse(raw_csv)

print(f"Indices parsed : {len(parsed.indices)}")
print()

# Show all parsed indices
print(f"{'canonical':20} {'broker_symbol':25} {'exchange':6} {'token':12}")
print("-" * 70)
for idx in parsed.indices:
    print(f"{idx.symbol:<20} {idx.broker_symbol:<25} {idx.exchange:<6} {idx.broker_token}")

print()

# Verify the 7 mapped indices are present with correct canonical names
print("Verifying INDEX_NAME_MAP entries:")
canonical_symbols = {idx.symbol for idx in parsed.indices}
for canonical, (exchange, broker_sym) in INDEX_NAME_MAP.items():
    found = canonical in canonical_symbols
    status = "✓" if found else "✗ MISSING"
    print(f"  {status}  {canonical}")

print()


# ---------------------------------------------------------------------------
# 2 & 3. DB schema + insert
# ---------------------------------------------------------------------------
async def run_db_test():
    print("=" * 60)
    print("2. DB SCHEMA + INSERT")
    print("=" * 60)

    Path("/tmp/tt_test_cache").mkdir(exist_ok=True)

    # Patch DB path to temp location
    import tt_connect.instrument_manager.db as db_module
    db_module.DB_PATH = Path("/tmp/tt_test_cache/instruments.db")
    if db_module.DB_PATH.exists():
        db_module.DB_PATH.unlink()

    conn = await get_connection()
    await init_schema(conn)

    # Verify all tables exist
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ) as cur:
        tables = [r[0] async for r in cur]
    print(f"Tables created : {tables}")

    # Verify broker_tokens has broker_symbol column
    async with conn.execute("PRAGMA table_info(broker_tokens)") as cur:
        cols = [r[1] async for r in cur]
    print(f"broker_tokens  : {cols}")

    # Verify instruments has segment column
    async with conn.execute("PRAGMA table_info(instruments)") as cur:
        cols = [r[1] async for r in cur]
    print(f"instruments    : {cols}")
    print()

    # Insert indices via manager
    manager = InstrumentManager(broker_id=BROKER_ID, on_stale=OnStale.FAIL)
    manager._conn = conn
    await manager._insert_indices(parsed.indices)

    # Verify counts
    async with conn.execute("SELECT COUNT(*) FROM instruments") as cur:
        count = (await cur.fetchone())[0]
    print(f"instruments rows   : {count}")

    async with conn.execute("SELECT COUNT(*) FROM equities") as cur:
        count = (await cur.fetchone())[0]
    print(f"equities rows      : {count}")

    async with conn.execute("SELECT COUNT(*) FROM broker_tokens") as cur:
        count = (await cur.fetchone())[0]
    print(f"broker_tokens rows : {count}")
    print()

    # ---------------------------------------------------------------------------
    # 4. Query — verify canonical vs broker symbol
    # ---------------------------------------------------------------------------
    print("=" * 60)
    print("4. CANONICAL vs BROKER SYMBOL")
    print("=" * 60)

    async with conn.execute("""
        SELECT i.symbol, bt.broker_symbol, bt.token, i.exchange
        FROM instruments i
        JOIN broker_tokens bt ON bt.instrument_id = i.id
        WHERE i.symbol != bt.broker_symbol
        ORDER BY i.exchange, i.symbol
    """) as cur:
        rows = await cur.fetchall()

    print(f"Rows where canonical ≠ broker_symbol: {len(rows)}")
    print(f"{'canonical':20} {'broker_symbol':25} {'exchange':6} {'token'}")
    print("-" * 70)
    for r in rows:
        print(f"{r[0]:<20} {r[1]:<25} {r[3]:<6} {r[2]}")
    print()

    # ---------------------------------------------------------------------------
    # 5. Resolver
    # ---------------------------------------------------------------------------
    print("=" * 60)
    print("5. RESOLVER")
    print("=" * 60)

    resolver = InstrumentResolver(conn, BROKER_ID)

    test_cases = [
        Index(exchange=Exchange.NSE, symbol="NIFTY"),
        Index(exchange=Exchange.NSE, symbol="BANKNIFTY"),
        Index(exchange=Exchange.NSE, symbol="FINNIFTY"),
        Index(exchange=Exchange.NSE, symbol="MIDCPNIFTY"),
        Index(exchange=Exchange.BSE, symbol="SENSEX"),
        Index(exchange=Exchange.BSE, symbol="BANKEX"),
    ]

    for instrument in test_cases:
        token = await resolver.resolve(instrument)
        print(f"  {instrument.symbol:<15} → token={token}")

    await conn.close()
    print()
    print("All checks passed.")

asyncio.run(run_db_test())
