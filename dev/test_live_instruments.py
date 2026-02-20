"""
Live integration test — instrument pipeline via the public AsyncTTConnect API.

Usage:
    python get_token.py           # if access_token is stale
    python test_live_instruments.py
"""

import asyncio
import os
import time
from pathlib import Path


def _load_env():
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env()

import tt_connect.instrument_manager.db as db_module
db_module.DB_PATH = Path("/tmp/tt_live_test/instruments.db")
Path("/tmp/tt_live_test").mkdir(exist_ok=True)
if db_module.DB_PATH.exists():
    db_module.DB_PATH.unlink()

from tt_connect.client import AsyncTTConnect
from tt_connect.instruments import Index, Equity
from tt_connect.enums import Exchange


async def run():
    config = {
        "api_key":      os.environ["ZERODHA_API_KEY"],
        "access_token": os.environ["ZERODHA_ACCESS_TOKEN"],
    }

    # -------------------------------------------------------------------
    # Init — this is the only call a user makes
    # -------------------------------------------------------------------
    print("Initialising broker (login + instrument download + DB insert) ...")
    t0 = time.perf_counter()

    broker = AsyncTTConnect("zerodha", config)
    await broker.init()

    print(f"Ready in {time.perf_counter() - t0:.1f}s")
    print()

    # -------------------------------------------------------------------
    # Verify DB via the connection the manager owns
    # -------------------------------------------------------------------
    conn = broker._instrument_manager.connection

    async def count(table, where=""):
        q = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
        async with conn.execute(q) as cur:
            return (await cur.fetchone())[0]

    print("DB counts:")
    total    = await count("instruments")
    indices  = await count("instruments", "segment = 'INDICES'")
    nse      = await count("instruments", "segment = 'NSE'")
    bse      = await count("instruments", "segment = 'BSE'")
    bt_total = await count("broker_tokens")
    print(f"  instruments   : {total}")
    print(f"    INDICES     : {indices}")
    print(f"    NSE stocks  : {nse}")
    print(f"    BSE stocks  : {bse}")
    print(f"  broker_tokens : {bt_total}")
    print()

    # -------------------------------------------------------------------
    # Resolver — the only way users look up tokens
    # -------------------------------------------------------------------
    print("Resolver spot-checks:")
    checks = [
        Index(exchange=Exchange.NSE,  symbol="NIFTY"),
        Index(exchange=Exchange.NSE,  symbol="BANKNIFTY"),
        Index(exchange=Exchange.BSE,  symbol="SENSEX"),
        Equity(exchange=Exchange.NSE, symbol="RELIANCE"),
        Equity(exchange=Exchange.NSE, symbol="INFY"),
        Equity(exchange=Exchange.BSE, symbol="TCS"),
    ]
    for inst in checks:
        token = await broker._resolve(inst)
        print(f"  {inst.exchange}:{inst.symbol:<15} → {token}")

    await broker.close()
    print()
    print("All checks passed.")


asyncio.run(run())
