import os

import pytest
import pytest_asyncio

from tt_connect.core.client._async import AsyncTTConnect

# --- Zerodha ---

@pytest.fixture
def broker_config() -> dict:
    return {
        "api_key":      os.environ.get("ZERODHA_API_KEY"),
        "access_token": os.environ.get("ZERODHA_ACCESS_TOKEN"),
    }

@pytest_asyncio.fixture
async def broker(broker_config: dict[str, str | None]):
    b = AsyncTTConnect("zerodha", broker_config)
    await b.init()
    yield b
    await b.close()

# --- AngelOne ---

@pytest.fixture(scope="module")
def angelone_config() -> dict:
    return {
        "auth_mode":    "auto",
        "api_key":      os.environ.get("ANGELONE_API_KEY"),
        "client_id":    os.environ.get("ANGELONE_CLIENT_ID"),
        "pin":          os.environ.get("ANGELONE_PIN"),
        "totp_secret":  os.environ.get("ANGELONE_TOTP_SECRET"),
    }

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def angelone_broker(angelone_config: dict[str, str | None]):
    async with AsyncTTConnect("angelone", angelone_config) as b:
        yield b

# --- Skip guard ---

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip live tests when required credentials are absent."""
    missing_zerodha  = not os.environ.get("ZERODHA_API_KEY") or not os.environ.get("ZERODHA_ACCESS_TOKEN")
    missing_angelone = (
        not os.environ.get("ANGELONE_API_KEY")
        or not os.environ.get("ANGELONE_CLIENT_ID")
        or not os.environ.get("ANGELONE_PIN")
        or not os.environ.get("ANGELONE_TOTP_SECRET")
    )

    for item in items:
        if "live" not in item.keywords:
            continue
        if "angelone_broker" in getattr(item, "fixturenames", []) and missing_angelone:
            item.add_marker(pytest.mark.skip(reason="ANGELONE credentials not set"))
        elif "broker" in getattr(item, "fixturenames", []) and missing_zerodha:
            item.add_marker(pytest.mark.skip(reason="ZERODHA credentials not set"))
