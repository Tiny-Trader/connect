import pytest
from tt_connect.adapters.zerodha.auth import ZerodhaAuth
from tt_connect.exceptions import AuthenticationError


def _make_auth(config: dict) -> ZerodhaAuth:
    return ZerodhaAuth(config, client=None)


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_sets_access_token():
    auth = _make_auth({"api_key": "testkey", "access_token": "testtoken"})
    await auth.login()
    assert auth.access_token == "testtoken"


@pytest.mark.asyncio
async def test_login_missing_token_raises():
    auth = _make_auth({"api_key": "testkey"})
    with pytest.raises(AuthenticationError):
        await auth.login()


@pytest.mark.asyncio
async def test_login_empty_token_raises():
    auth = _make_auth({"api_key": "testkey", "access_token": ""})
    with pytest.raises(AuthenticationError):
        await auth.login()


# ---------------------------------------------------------------------------
# headers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_headers_format():
    auth = _make_auth({"api_key": "mykey", "access_token": "mytoken"})
    await auth.login()
    headers = auth.headers
    assert headers["X-Kite-Version"] == "3"
    assert headers["Authorization"] == "token mykey:mytoken"


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_reads_config_token():
    auth = _make_auth({"api_key": "testkey", "access_token": "tok1"})
    await auth.login()

    # Simulate user updating the token in config (new day)
    auth._config["access_token"] = "tok2"
    await auth.refresh()

    assert auth.access_token == "tok2"
