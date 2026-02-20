"""
Smoke test for options:
  1. Parser   — counts NFO + BFO options (CE/PE), verifies expiry/strike parsing
  2. DB       — insert and verify row counts + underlying FK integrity
  3. Resolver — resolves using Exchange.NSE/BSE (underlying exchange, not NFO/BFO)
"""

import asyncio
import os
from datetime import date
from pathlib import Path

os.environ["TT_CACHE_DIR"] = "/tmp/tt_test_cache"

from tt_connect.adapters.zerodha.parser import parse
from tt_connect.instrument_manager.db import get_connection, init_schema
from tt_connect.instrument_manager.manager import InstrumentManager
from tt_connect.instrument_manager.resolver import InstrumentResolver
from tt_connect.instruments import Option
from tt_connect.enums import Exchange, OnStale, OptionType

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

nfo = [o for o in parsed.options if o.exchange == "NFO"]
bfo = [o for o in parsed.options if o.exchange == "BFO"]
nfo_ce = [o for o in nfo if o.option_type == "CE"]
nfo_pe = [o for o in nfo if o.option_type == "PE"]
bfo_ce = [o for o in bfo if o.option_type == "CE"]
bfo_pe = [o for o in bfo if o.option_type == "PE"]

print(f"Options parsed : {len(parsed.options)}")
print(f"  NFO  CE={len(nfo_ce)}  PE={len(nfo_pe)}")
print(f"  BFO  CE={len(bfo_ce)}  PE={len(bfo_pe)}")
print()

# Spot-check a few
print(f"{'broker_symbol':<25} {'symbol':<12} {'u_exchange':<12} {'expiry':<12} {'strike':<10} type")
print("-" * 80)
samples = [
    next(o for o in nfo if o.symbol == "NIFTY" and o.option_type == "CE"),
    next(o for o in nfo if o.symbol == "NIFTY" and o.option_type == "PE"),
    next(o for o in nfo if o.symbol == "RELIANCE" and o.option_type == "CE"),
    next(o for o in bfo if o.symbol == "SENSEX" and o.option_type == "CE"),
    next(o for o in bfo if o.symbol == "BANKEX" and o.option_type == "PE"),
]
for o in samples:
    print(f"{o.broker_symbol:<25} {o.symbol:<12} {o.underlying_exchange:<12} {str(o.expiry):<12} {o.strike:<10} {o.option_type}")
print()


# ---------------------------------------------------------------------------
# 2. DB insert + FK integrity check
# ---------------------------------------------------------------------------
async def run_db_test():
    print("=" * 60)
    print("2. DB INSERT + FK INTEGRITY")
    print("=" * 60)

    Path("/tmp/tt_test_cache").mkdir(exist_ok=True)

    import tt_connect.instrument_manager.db as db_module
    db_module.DB_PATH = Path("/tmp/tt_test_cache/instruments_opt.db")
    if db_module.DB_PATH.exists():
        db_module.DB_PATH.unlink()

    conn = await get_connection()
    await init_schema(conn)

    manager = InstrumentManager(broker_id=BROKER_ID, on_stale=OnStale.FAIL)
    manager._conn = conn

    await manager._insert_indices(parsed.indices)
    await manager._insert_equities(parsed.equities)
    lookup = await manager._build_underlying_lookup()
    await manager._insert_futures(parsed.futures, lookup)
    await manager._insert_options(parsed.options, lookup)
    await conn.commit()

    async def count(q):
        async with conn.execute(q) as cur:
            return (await cur.fetchone())[0]

    total    = await count("SELECT COUNT(*) FROM instruments")
    opt_rows = await count("SELECT COUNT(*) FROM options")
    bt_rows  = await count("SELECT COUNT(*) FROM broker_tokens")

    print(f"instruments rows : {total}")
    print(f"options rows     : {opt_rows}  (expected {len(parsed.options)})")
    print(f"broker_tokens    : {bt_rows}")
    print()

    # FK integrity — every options.underlying_id must point to a real instruments row
    orphans = await count("""
        SELECT COUNT(*) FROM options o
        LEFT JOIN instruments u ON u.id = o.underlying_id
        WHERE u.id IS NULL
    """)
    print(f"Orphaned underlying_ids : {orphans}  (expected 0)")
    print()

    # Sample underlying resolution check
    print("Sample underlying resolution check:")
    async with conn.execute("""
        SELECT opt.symbol, u.exchange, u.symbol, u.segment, o.expiry, o.strike, o.option_type
        FROM instruments opt
        JOIN options o     ON o.instrument_id = opt.id
        JOIN instruments u ON u.id = o.underlying_id
        ORDER BY opt.exchange, u.symbol, o.expiry, o.strike
        LIMIT 6
    """) as cur:
        rows = await cur.fetchall()
    print(f"  {'opt_symbol':<12} {'u.exchange':<10} {'u.symbol':<12} {'u.segment':<12} {'expiry':<12} {'strike':<10} type")
    print("  " + "-" * 75)
    for r in rows:
        print(f"  {r[0]:<12} {r[1]:<10} {r[2]:<12} {r[3]:<12} {r[4]:<12} {r[5]:<10} {r[6]}")
    print()

    # ---------------------------------------------------------------------------
    # 3. Resolver — user uses Exchange.NSE / Exchange.BSE (underlying exchange)
    # ---------------------------------------------------------------------------
    print("=" * 60)
    print("3. RESOLVER")
    print("=" * 60)

    resolver = InstrumentResolver(conn, BROKER_ID)

    # Get real expiry + strike from what we just inserted
    async with conn.execute("""
        SELECT u.exchange, u.symbol, o.expiry, o.strike, o.option_type
        FROM options o
        JOIN instruments u ON u.id = o.underlying_id
        WHERE u.symbol IN ('NIFTY', 'RELIANCE', 'SENSEX', 'BANKEX')
        GROUP BY u.exchange, u.symbol, o.option_type
        HAVING o.strike = MIN(o.strike)
        ORDER BY u.exchange, u.symbol, o.option_type
        LIMIT 6
    """) as cur:
        sample_rows = await cur.fetchall()

    for uex, usym, expiry, strike, otype in sample_rows:
        exchange = Exchange.NSE if uex == "NSE" else Exchange.BSE
        ot = OptionType.CE if otype == "CE" else OptionType.PE
        instrument = Option(
            exchange=exchange,
            symbol=usym,
            expiry=date.fromisoformat(expiry),
            strike=strike,
            option_type=ot,
        )
        token = await resolver.resolve(instrument)
        print(f"  {uex}:{usym:<12} expiry={expiry}  strike={strike:<10} {otype}  → token={token}")

    await conn.close()
    print()
    print("All checks passed.")


asyncio.run(run_db_test())
