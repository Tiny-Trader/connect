"""
Dev helper — fetch a fresh Zerodha access_token using credentials from .env.

Usage:
    pip install pyotp          # one-time, if not already installed
    python get_token.py

Writes ZERODHA_ACCESS_TOKEN back into .env so test_live_auth.py picks it up.
"""

import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
import pyotp


# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------

def _load_env():
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        raise SystemExit("No .env found. Copy .env.example → .env and fill in credentials.")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env()

API_KEY    = os.environ["ZERODHA_API_KEY"]
API_SECRET = os.environ["ZERODHA_API_SECRET"]
USER_ID    = os.environ["ZERODHA_USER_ID"]
PASSWORD   = os.environ["ZERODHA_PASSWORD"]
TOTP_KEY   = os.environ["ZERODHA_TOTP_KEY"]


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def get_access_token() -> str:
    client = httpx.Client(follow_redirects=False)

    # Step 1: Establish connect session — follow the full redirect chain
    # First GET returns 302 to connect/login?sess_id=xxx; follow to bind sess_id to session
    print("Step 1: init connect session ...")
    r = client.get(f"https://kite.zerodha.com/connect/login?api_key={API_KEY}&v=3")
    sess_id = None
    if r.status_code == 302:
        location = r.headers["location"]
        qs = parse_qs(urlparse(location).query)
        sess_id = qs.get("sess_id", [None])[0]
        r = client.get(location)
    print(f"   sess_id : {sess_id[:8]}...")

    # Step 2: userid + password → request_id
    print("Step 2: password login ...")
    resp = client.post(
        "https://kite.zerodha.com/api/login",
        data={"user_id": USER_ID, "password": PASSWORD},
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != "success":
        raise SystemExit(f"Login failed: {body.get('message', body)}")
    request_id = body["data"]["request_id"]
    print(f"   request_id : {request_id[:8]}...")

    # Step 3: TOTP → redirects to redirect_url?request_token=xxx
    print("Step 3: TOTP ...")
    totp = pyotp.TOTP(TOTP_KEY).now()
    print(f"   totp       : {totp}")
    resp = client.post(
        "https://kite.zerodha.com/api/twofa",
        data={
            "user_id":     USER_ID,
            "request_id":  request_id,
            "twofa_value": totp,
            "twofa_type":  "totp",
        },
    )
    if resp.status_code != 200 or resp.json().get("status") != "success":
        raise SystemExit(f"TOTP step failed ({resp.status_code}): {resp.text}")

    # Step 4: Finalize connect session — follow redirect chain until request_token appears
    print("Step 4: finalize connect session ...")
    next_url = f"https://kite.zerodha.com/connect/login?api_key={API_KEY}&sess_id={sess_id}"
    request_token = None
    for _ in range(5):
        r = client.get(next_url)
        location = r.headers.get("location", "")
        qs = parse_qs(urlparse(location).query)
        if "request_token" in qs:
            request_token = qs["request_token"][0]
            break
        if not location or r.status_code != 302:
            break
        next_url = location

    if not request_token:
        raise SystemExit(f"request_token not found after redirect chain")
    print(f"   request_token : {request_token[:8]}...")

    # Step 5: Exchange request_token → access_token
    print("Step 5: token exchange ...")
    checksum = hashlib.sha256(
        f"{API_KEY}{request_token}{API_SECRET}".encode()
    ).hexdigest()
    resp = httpx.post(
        "https://api.kite.trade/session/token",
        data={"api_key": API_KEY, "request_token": request_token, "checksum": checksum},
        headers={"X-Kite-Version": "3"},
    )
    resp.raise_for_status()
    body = resp.json()
    if "data" not in body or "access_token" not in body["data"]:
        raise SystemExit(f"Token exchange failed: {body}")

    return body["data"]["access_token"]


# ---------------------------------------------------------------------------
# Write back to .env
# ---------------------------------------------------------------------------

def _update_env(access_token: str) -> None:
    env_path = Path(__file__).parent.parent / ".env"
    text = env_path.read_text()
    if re.search(r"^ZERODHA_ACCESS_TOKEN=", text, re.MULTILINE):
        text = re.sub(
            r"^ZERODHA_ACCESS_TOKEN=.*$",
            f"ZERODHA_ACCESS_TOKEN={access_token}",
            text,
            flags=re.MULTILINE,
        )
    else:
        text += f"\nZERODHA_ACCESS_TOKEN={access_token}\n"
    env_path.write_text(text)


if __name__ == "__main__":
    token = get_access_token()
    _update_env(token)
    print()
    print(f"access_token : {token[:6]}...{token[-4:]}")
    print(".env updated — run test_live_auth.py to verify.")
