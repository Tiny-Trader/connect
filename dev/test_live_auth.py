"""
Live integration test for Zerodha auth + profile call.

Setup:
    cp .env.example .env
    # fill in your api_key and access_token
    python test_live_auth.py

Does NOT download the instrument CSV — just validates:
  1. Token accepted by Zerodha (GET /user/profile)
  2. Funds endpoint reachable (GET /user/margins)
  3. Authorization header format is correct
"""

import asyncio
import os
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

API_KEY      = os.environ.get("ZERODHA_API_KEY")
ACCESS_TOKEN = os.environ.get("ZERODHA_ACCESS_TOKEN")

if not API_KEY or not ACCESS_TOKEN:
    raise SystemExit(
        "Missing credentials.\n"
        "Copy .env.example → .env and fill in ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN."
    )

from tt_connect.adapters.zerodha.auth import ZerodhaAuth
from tt_connect.adapters.zerodha.adapter import ZerodhaAdapter


async def run():
    config = {"api_key": API_KEY, "access_token": ACCESS_TOKEN}
    adapter = ZerodhaAdapter(config)

    # --- Auth ---
    print("1. login()")
    await adapter.login()
    print(f"   access_token set : {adapter.auth._access_token[:6]}...{adapter.auth._access_token[-4:]}")
    print(f"   headers          : {adapter.auth.headers}")
    print()

    # --- Profile ---
    print("2. GET /user/profile")
    raw = await adapter.get_profile()
    data = raw["data"]
    print(f"   user_id  : {data['user_id']}")
    print(f"   name     : {data['user_name']}")
    print(f"   email    : {data['email']}")
    print(f"   broker   : {data['broker']}")
    print()

    # --- Funds ---
    print("3. GET /user/margins")
    raw = await adapter.get_funds()
    equity = raw["data"].get("equity", {})
    print(f"   available cash : {equity.get('available', {}).get('cash', 'n/a')}")
    print()

    print("All live checks passed.")


asyncio.run(run())
