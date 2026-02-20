"""
Smoke test for equities:
  1. Parser  — counts NSE + BSE equities from CSV
  2. DB      — insert and verify row counts
  3. Resolver — resolves a handful of well-known stocks
"""

import asyncio
import os
from pathlib import Path

os.environ["TT_CACHE_DIR"] = "/tmp/tt_test_cache"

from tt_connect.adapters.zerodha.parser import parse
from tt_connect.instrument_manager.db import get_connection, init_schema
from tt_connect.instrument_manager.manager import InstrumentManager
from tt_connect.instrument_manager.resolver import InstrumentResolver
from tt_connect.instruments import Equity
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

nse = [e for e in parsed.equities if e.exchange == "NSE"]
bse = [e for e in parsed.equities if e.exchange == "BSE"]

print(f"Equities parsed : {len(parsed.equities)}  (NSE={len(nse)}, BSE={len(bse)})")
print()

# Verify well-known symbols are present
check_symbols = ["RELIANCE", "INFY", "TCS", "HDFCBANK", "WIPRO"]
print("Spot-checking NSE symbols:")
nse_symbols = {e.symbol for e in nse}
for sym in check_symbols:
    status = "✓" if sym in nse_symbols else "✗ MISSING"
    print(f"  {status}  {sym}")
print()


# ---------------------------------------------------------------------------
# 2. DB insert
# ---------------------------------------------------------------------------
async def run_db_test():
    print("=" * 60)
    print("2. DB INSERT")
    print("=" * 60)

    Path("/tmp/tt_test_cache").mkdir(exist_ok=True)

    import tt_connect.instrument_manager.db as db_module
    db_module.DB_PATH = Path("/tmp/tt_test_cache/instruments_eq.db")
    if db_module.DB_PATH.exists():
        db_module.DB_PATH.unlink()

    conn = await get_connection()
    await init_schema(conn)

    manager = InstrumentManager(broker_id=BROKER_ID, on_stale=OnStale.FAIL)
    manager._conn = conn
    await manager._insert_indices(parsed.indices)
    await manager._insert_equities(parsed.equities)
    await conn.commit()

    async with conn.execute("SELECT COUNT(*) FROM instruments") as cur:
        total = (await cur.fetchone())[0]
    async with conn.execute("SELECT COUNT(*) FROM equities") as cur:
        eq_count = (await cur.fetchone())[0]
    async with conn.execute("SELECT COUNT(*) FROM broker_tokens") as cur:
        bt_count = (await cur.fetchone())[0]

    print(f"instruments rows   : {total}   (expected ~{len(parsed.indices) + len(parsed.equities)})")
    print(f"equities rows      : {eq_count}")
    print(f"broker_tokens rows : {bt_count}")
    print()

    # ---------------------------------------------------------------------------
    # 3. Resolver
    # ---------------------------------------------------------------------------
    print("=" * 60)
    print("3. RESOLVER")
    print("=" * 60)

    resolver = InstrumentResolver(conn, BROKER_ID)

    test_cases = [
        Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        Equity(exchange=Exchange.NSE, symbol="INFY"),
        Equity(exchange=Exchange.NSE, symbol="TCS"),
        Equity(exchange=Exchange.BSE, symbol="RELIANCE"),
        Equity(exchange=Exchange.BSE, symbol="INFY"),
    ]

    for instrument in test_cases:
        token = await resolver.resolve(instrument)
        print(f"  {instrument.exchange}:{instrument.symbol:<15} → token={token}")

    await conn.close()
    print()
    print("All checks passed.")

asyncio.run(run_db_test())
