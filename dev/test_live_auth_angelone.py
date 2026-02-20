"""
Live integration test — AngelOne Auth & Profile.

Usage:
    python dev/test_live_auth_angelone.py
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

from tt_connect.client import AsyncTTConnect

async def run():
    config = {
        "api_key":      os.environ.get("ANGELONE_API_KEY"),
        "client_id":    os.environ.get("ANGELONE_CLIENT_ID"),
        "pin":          os.environ.get("ANGELONE_PIN"),
        "totp_secret":  os.environ.get("ANGELONE_TOTP_SECRET"),
    }

    if not all(config.values()):
        print("Missing AngelOne credentials in .env")
        return

    print(f"Testing AngelOne login for {config['client_id']}...")
    
    # We use AsyncTTConnect which internally uses the AngelOneAdapter
    broker = AsyncTTConnect("angelone", config)
    
    try:
        # 1. Login
        await broker._adapter.login()
        print("✓ Login successful")

        # 2. Get Profile
        profile_raw = await broker._adapter.get_profile()
        print(f"✓ Profile fetch successful: {profile_raw.get('data', {}).get('name')}")

        # 3. Get Funds
        funds_raw = await broker._adapter.get_funds()
        print(f"✓ Funds fetch successful")
        # print(funds_raw)

    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        # Avoid closing uninitialized instrument manager
        try:
            if broker._instrument_manager._conn:
                await broker.close()
            else:
                await broker._adapter._client.aclose()
        except Exception:
            await broker._adapter._client.aclose()

if __name__ == "__main__":
    asyncio.run(run())
