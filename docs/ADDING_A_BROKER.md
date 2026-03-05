# Adding a New Broker

This guide walks through every step of adding a new broker to tt-connect. The example uses a fictional broker called **Dhan** — replace with your broker's name throughout.

## Prerequisites

Before you start, you need:

1. **API documentation** for the broker (REST endpoints, auth flow, error codes).
2. **Instrument master file** — the broker's downloadable instrument list (CSV, JSON, or API endpoint).
3. **WebSocket documentation** — if the broker supports real-time streaming.
4. A working `tt-connect` dev environment (`poetry install`).

---

## TL;DR

```
brokers/dhan/
├── __init__.py          # 2 import lines — triggers registration
├── config.py            # Pydantic config model (extends BrokerConfig)
├── capabilities.py      # Supported segments, order types, product types
├── auth.py              # Authentication flow (extends BaseAuth)
├── adapter.py           # REST endpoint wiring (extends BrokerAdapter)
├── transformer.py       # Request/response normalization
├── parser.py            # Instrument master file parsing
└── ws.py                # WebSocket client (extends BrokerWebSocket)
```

Create these 8 files. Touch nothing outside `brokers/dhan/`. Tests go in `tests/unit/brokers/dhan/`.

---

## Step 1: Create the Broker Package

```bash
mkdir -p tt_connect/brokers/dhan
mkdir -p tests/unit/brokers/dhan
```

---

## Step 2: `__init__.py` — Registration Trigger

This file's only job is to import the adapter and config modules, which triggers their `__init_subclass__` auto-registration.

```python
# tt_connect/brokers/dhan/__init__.py

"""Dhan broker package — triggers adapter + config registration on import."""

import tt_connect.brokers.dhan.adapter  # noqa: F401 — triggers BrokerAdapter registration
import tt_connect.brokers.dhan.config   # noqa: F401 — triggers BrokerConfig registration
```

> **How discovery works:** `tt_connect/brokers/__init__.py` uses `pkgutil.iter_modules` to find all subpackages and imports them. Your `__init__.py` runs automatically — you don't need to edit any file outside your folder.

---

## Step 3: `config.py` — Configuration Model

Define a Pydantic model for the broker's required credentials. The `broker_id` keyword triggers auto-registration into `BrokerConfig._registry`.

```python
# tt_connect/brokers/dhan/config.py

"""Validated configuration for Dhan."""

from pydantic import model_validator
from tt_connect.core.models.config import BrokerConfig
from tt_connect.core.models.enums import AuthMode


class DhanConfig(BrokerConfig, broker_id="dhan"):
    """Configuration for Dhan API.

    AUTO mode — library performs login automatically:
        client_id, access_token  (both required)

    MANUAL mode — supply a pre-obtained token:
        access_token  (required)
    """

    auth_mode: AuthMode = AuthMode.MANUAL
    client_id: str | None = None
    access_token: str | None = None

    @model_validator(mode="after")
    def _check_credentials(self) -> "DhanConfig":
        if self.auth_mode == AuthMode.AUTO:
            if not self.client_id or not self.access_token:
                raise ValueError("Dhan AUTO mode requires 'client_id' and 'access_token'")
        else:
            if not self.access_token:
                raise ValueError("Dhan MANUAL mode requires 'access_token'")
        return self
```

**Key rules:**

- Extend `BrokerConfig` and pass `broker_id="dhan"` — this registers the config class.
- Use `model_config = ConfigDict(extra="forbid")` is inherited — typos in config keys will raise.
- Add a `@model_validator` to enforce mode-specific required fields.
- The `on_stale` and `cache_session` fields are inherited from `BrokerConfig`.

---

## Step 4: `capabilities.py` — Feature Matrix

Declare what segments, order types, and product types the broker supports. The client uses this to fail fast before making network calls.

```python
# tt_connect/brokers/dhan/capabilities.py

"""Dhan capability matrix."""

from tt_connect.core.adapter.capabilities import Capabilities
from tt_connect.core.models.enums import Exchange, OrderType, ProductType, AuthMode

DHAN_CAPABILITIES = Capabilities(
    broker_id="dhan",
    segments=frozenset({Exchange.NSE, Exchange.BSE, Exchange.NFO, Exchange.BFO}),
    order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.SL, OrderType.SL_M}),
    product_types=frozenset({ProductType.CNC, ProductType.MIS, ProductType.NRML}),
    auth_modes=frozenset({AuthMode.MANUAL}),
)
```

**Reference:** Look at the broker's API docs to determine:

- Which exchanges they support → `segments`
- Which order types (market, limit, SL, SL-M) → `order_types`
- Which product types (CNC, MIS, NRML, BO, CO) → `product_types`
- Whether they support auto-login (TOTP/OAuth) or manual only → `auth_modes`

---

## Step 5: `auth.py` — Authentication

Extend `BaseAuth` and implement the login flow. Set the class variables to declare supported modes.

```python
# tt_connect/brokers/dhan/auth.py

"""Dhan authentication implementation."""

from __future__ import annotations

from tt_connect.core.adapter.auth import BaseAuth, SessionData, next_midnight_ist
from tt_connect.core.models.enums import AuthMode
from tt_connect.core.exceptions import AuthenticationError


class DhanAuth(BaseAuth):
    """Manual-token auth flow for Dhan."""

    _broker_id = "dhan"
    _default_mode = AuthMode.MANUAL
    _supported_modes = frozenset({AuthMode.MANUAL})

    async def _login_manual(self) -> None:
        """Load access_token from config and create session state."""
        token = self._config.get("access_token")
        if not token:
            raise AuthenticationError(
                "Dhan requires 'access_token' in config."
            )
        self._session = SessionData(
            access_token=token,
            expires_at=next_midnight_ist(),
        )

    @property
    def headers(self) -> dict[str, str]:
        """Build authenticated headers expected by Dhan APIs."""
        return {
            "Content-Type": "application/json",
            "access-token": self.access_token or "",
            "client-id": self._config.get("client_id", ""),
        }
```

**Key rules:**

- `_broker_id`: string identifier, must match the `broker_id` used elsewhere.
- `_default_mode`: which mode to use when user doesn't specify `auth_mode` in config.
- `_supported_modes`: frozenset of modes this broker supports.
- Override `_login_manual()` for manual token flow.
- Override `_login_auto()` if the broker supports automated login (TOTP, OAuth, etc.).
- Override `_refresh_auto()` if the broker supports token refresh.
- The `headers` property must return a dict that gets passed to every REST call.

---

## Step 6: `adapter.py` — REST Endpoint Wiring

This is the main class — it extends `BrokerAdapter` and wires each REST method to the broker's API endpoints.

```python
# tt_connect/brokers/dhan/adapter.py

"""Dhan REST adapter implementation."""

from tt_connect.core.adapter.base import BrokerAdapter
from tt_connect.core.adapter.transformer import JsonDict
from tt_connect.core.adapter.capabilities import Capabilities
from tt_connect.core.adapter.ws import BrokerWebSocket
from tt_connect.core.models.config import validate_config
from tt_connect.core.exceptions import AuthenticationError

from tt_connect.brokers.dhan.auth import DhanAuth
from tt_connect.brokers.dhan.transformer import DhanTransformer
from tt_connect.brokers.dhan.capabilities import DHAN_CAPABILITIES
from tt_connect.brokers.dhan.parser import parse, ParsedInstruments

BASE_URL = "https://api.dhan.co/v2"


class DhanAdapter(BrokerAdapter, broker_id="dhan"):
    """Broker adapter for Dhan APIs."""

    def __init__(self, config: JsonDict):
        validate_config("dhan", config)
        super().__init__(config)
        self.auth = DhanAuth(config, self._client)
        self._transformer = DhanTransformer()

    @property
    def transformer(self) -> DhanTransformer:
        return self._transformer

    @property
    def capabilities(self) -> Capabilities:
        return DHAN_CAPABILITIES

    # --- Lifecycle ---

    async def login(self) -> None:
        await self.auth.login()

    async def refresh_session(self) -> None:
        await self.auth.refresh()

    async def fetch_instruments(self) -> ParsedInstruments:
        """Download and parse the instrument master."""
        response = await self._client.get(f"{BASE_URL}/instruments")
        response.raise_for_status()
        return parse(response.json())

    # --- REST endpoints ---

    async def get_profile(self) -> JsonDict:
        return await self._request("GET", f"{BASE_URL}/clients/profile",
                                   headers=self.auth.headers)

    async def get_funds(self) -> JsonDict:
        return await self._request("GET", f"{BASE_URL}/fundlimit",
                                   headers=self.auth.headers)

    async def get_holdings(self) -> JsonDict:
        return await self._request("GET", f"{BASE_URL}/holdings",
                                   headers=self.auth.headers)

    async def get_positions(self) -> JsonDict:
        raw = await self._request("GET", f"{BASE_URL}/positions",
                                  headers=self.auth.headers)
        # Filter out flat positions if needed
        raw["data"] = [p for p in raw["data"] if p.get("netQty", 0) != 0]
        return raw

    async def get_trades(self) -> JsonDict:
        return await self._request("GET", f"{BASE_URL}/trades",
                                   headers=self.auth.headers)

    async def place_order(self, params: JsonDict) -> JsonDict:
        return await self._request("POST", f"{BASE_URL}/orders",
                                   headers=self.auth.headers, json=params)

    async def modify_order(self, order_id: str, params: JsonDict) -> JsonDict:
        return await self._request("PUT", f"{BASE_URL}/orders/{order_id}",
                                   headers=self.auth.headers, json=params)

    async def cancel_order(self, order_id: str) -> JsonDict:
        return await self._request("DELETE", f"{BASE_URL}/orders/{order_id}",
                                   headers=self.auth.headers)

    async def get_order(self, order_id: str) -> JsonDict:
        return await self._request("GET", f"{BASE_URL}/orders/{order_id}",
                                   headers=self.auth.headers)

    async def get_orders(self) -> JsonDict:
        return await self._request("GET", f"{BASE_URL}/orders",
                                   headers=self.auth.headers)

    # --- WebSocket (optional) ---

    def create_ws_client(self) -> BrokerWebSocket:
        from tt_connect.brokers.dhan.ws import DhanWebSocket
        access_token = str(self.auth.access_token or "").strip()
        if not access_token:
            raise AuthenticationError("Cannot create Dhan WebSocket: missing access_token")
        return DhanWebSocket(access_token=access_token)

    # --- Internal ---

    def _is_error(self, raw: JsonDict, status_code: int) -> bool:
        """Identify broker-level errors in the response envelope."""
        return raw.get("status") == "error" or status_code >= 400
```

**Key rules:**

- Pass `broker_id="dhan"` to `BrokerAdapter` — this auto-registers the adapter.
- Call `validate_config("dhan", config)` in `__init__` to enforce the config model.
- Every REST method must return a `JsonDict` with at least a `"data"` key.
- `_is_error()` tells the base class which responses are errors (triggers `transformer.parse_error()`).
- GTT methods (`place_gtt`, `modify_gtt`, etc.) are optional — the base class raises `UnsupportedFeatureError` by default.
- `get_historical()` and `get_quotes()` are also optional — override only if the broker supports them.

---

## Step 7: `transformer.py` — Request/Response Normalization

This is typically the largest file. It converts between the broker's raw JSON and tt-connect's canonical models.

```python
# tt_connect/brokers/dhan/transformer.py

"""Dhan request/response normalization."""

from datetime import datetime
from typing import Any

from tt_connect.core.models import (
    Candle, Fund, GetHistoricalRequest, Gtt, GttLeg,
    Holding, ModifyGttRequest, ModifyOrderRequest, Order,
    PlaceGttRequest, PlaceOrderRequest, Position, Profile, Tick, Trade,
)
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.models.enums import (
    Exchange, OrderStatus, OrderType, ProductType, Side,
)
from tt_connect.core.exceptions import (
    TTConnectError, AuthenticationError, OrderError, BrokerError,
)

# Map the broker's error codes to tt-connect exception types
ERROR_MAP: dict[str, type[TTConnectError]] = {
    "TOKEN_EXPIRED":  AuthenticationError,
    "INVALID_ORDER":  OrderError,
    # ... add all error codes from the broker's API docs
}

# Map broker's order status strings to canonical OrderStatus
_ORDER_STATUS_MAP: dict[str, OrderStatus] = {
    "TRADED":     OrderStatus.COMPLETE,
    "REJECTED":   OrderStatus.REJECTED,
    "CANCELLED":  OrderStatus.CANCELLED,
    "PENDING":    OrderStatus.PENDING,
    "TRANSIT":    OrderStatus.PENDING,
    # ... add all status values from the broker's API docs
}


class DhanTransformer:
    """Transforms Dhan raw payloads to/from canonical tt-connect models."""

    # ---------------------------------------------------------------- Outgoing
    # These methods build broker-native request payloads from canonical models.

    @staticmethod
    def to_order_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceOrderRequest,
    ) -> dict[str, Any]:
        """Build Dhan order placement payload."""
        params: dict[str, Any] = {
            "securityId":      token,
            "exchangeSegment": exchange,
            "transactionType": "BUY" if req.side == Side.BUY else "SELL",
            "quantity":        req.qty,
            "productType":     req.product.value,
            "orderType":       req.order_type.value,
            "validity":        "DAY",
        }
        if req.price:
            params["price"] = req.price
        if req.trigger_price:
            params["triggerPrice"] = req.trigger_price
        return params

    @staticmethod
    def to_modify_params(req: ModifyOrderRequest) -> dict[str, Any]:
        """Build Dhan order modification payload."""
        params: dict[str, Any] = {"orderId": req.order_id}
        if req.qty is not None:
            params["quantity"] = req.qty
        if req.price is not None:
            params["price"] = req.price
        if req.trigger_price is not None:
            params["triggerPrice"] = req.trigger_price
        if req.order_type is not None:
            params["orderType"] = req.order_type.value
        return params

    @staticmethod
    def to_order_id(raw: dict[str, Any]) -> str:
        """Extract order ID from broker response."""
        return str(raw["data"]["orderId"])

    @staticmethod
    def to_close_position_params(
        pos_raw: dict[str, Any], qty: int, side: Side,
    ) -> dict[str, Any]:
        """Build market order to close a position."""
        return {
            "securityId":      pos_raw["securityId"],
            "exchangeSegment": pos_raw["exchangeSegment"],
            "transactionType": "BUY" if side == Side.BUY else "SELL",
            "quantity":        qty,
            "productType":     pos_raw["productType"],
            "orderType":       "MARKET",
            "validity":        "DAY",
        }

    # ---------------------------------------------------------------- Incoming
    # These methods normalize broker responses into canonical models.

    @staticmethod
    def to_profile(raw: dict[str, Any]) -> Profile:
        return Profile(
            client_id=raw["clientId"],
            name=raw["name"],
            email=raw["email"],
            phone=raw.get("mobile"),
        )

    @staticmethod
    def to_fund(raw: dict[str, Any]) -> Fund:
        return Fund(
            available=float(raw["availableFund"]),
            used=float(raw["utilizedFund"]),
            total=float(raw["availableFund"]) + float(raw["utilizedFund"]),
        )

    @staticmethod
    def to_holding(raw: dict[str, Any]) -> Holding:
        avg = float(raw["avgCostPrice"])
        ltp = float(raw["currentPrice"])
        pnl = float(raw.get("unrealizedProfit", 0))
        pnl_pct = round((ltp - avg) / avg * 100, 2) if avg else 0.0
        return Holding(
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=raw["tradingSymbol"],
            ),
            qty=int(raw["totalQty"]),
            avg_price=avg,
            ltp=ltp,
            pnl=pnl,
            pnl_percent=pnl_pct,
        )

    @staticmethod
    def to_position(raw: dict[str, Any]) -> Position:
        return Position(
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=raw["tradingSymbol"],
            ),
            qty=int(raw["netQty"]),
            avg_price=float(raw["avgPrice"]),
            ltp=float(raw["lastPrice"]),
            pnl=float(raw.get("realizedProfit", 0)),
            product=ProductType(raw["productType"]),
        )

    @staticmethod
    def to_trade(raw: dict[str, Any]) -> Trade:
        ts_str = raw.get("tradedTime")
        return Trade(
            order_id=str(raw["orderId"]),
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=raw["tradingSymbol"],
            ),
            side=Side.BUY if raw["transactionType"] == "BUY" else Side.SELL,
            qty=int(raw["tradedQty"]),
            avg_price=float(raw["tradedPrice"]),
            trade_value=round(float(raw["tradedQty"]) * float(raw["tradedPrice"]), 2),
            product=ProductType(raw["productType"]),
            timestamp=datetime.fromisoformat(ts_str) if ts_str else None,
        )

    @staticmethod
    def to_order(raw: dict[str, Any], instrument: Any = None) -> Order:
        status = _ORDER_STATUS_MAP.get(raw["orderStatus"], OrderStatus.PENDING)
        ts_str = raw.get("createTime")
        return Order(
            id=str(raw["orderId"]),
            instrument=instrument,
            side=Side.BUY if raw["transactionType"] == "BUY" else Side.SELL,
            qty=int(raw["quantity"]),
            filled_qty=int(raw.get("filledQty", 0)),
            product=ProductType(raw["productType"]),
            order_type=OrderType(raw["orderType"]),
            status=status,
            price=float(raw["price"]) if raw.get("price") else None,
            trigger_price=float(raw["triggerPrice"]) if raw.get("triggerPrice") else None,
            avg_price=float(raw["avgTradedPrice"]) if raw.get("avgTradedPrice") else None,
            timestamp=datetime.fromisoformat(ts_str) if ts_str else None,
        )

    # ------------------------------------------------------------ Historical

    @staticmethod
    def to_historical_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: GetHistoricalRequest,
    ) -> dict[str, Any]:
        return {
            "securityId":      token,
            "exchangeSegment": exchange,
            "instrument":      "EQUITY",
            "fromDate":        req.from_date.strftime("%Y-%m-%d"),
            "toDate":          req.to_date.strftime("%Y-%m-%d"),
        }

    @staticmethod
    def to_candles(rows: list[Any], instrument: Any) -> list[Candle]:
        return [
            Candle(
                instrument=instrument,
                timestamp=datetime.fromisoformat(str(row["timestamp"])),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                oi=int(row["oi"]) if row.get("oi") else None,
            )
            for row in rows
        ]

    @staticmethod
    def to_quote(raw: dict[str, Any], instrument: Any) -> Tick:
        return Tick(
            instrument=instrument,
            ltp=float(raw["lastPrice"]),
            volume=raw.get("volume"),
            oi=raw.get("oi"),
            bid=float(raw["bestBidPrice"]) if raw.get("bestBidPrice") else None,
            ask=float(raw["bestAskPrice"]) if raw.get("bestAskPrice") else None,
        )

    # ---------------------------------------------------------------- GTT
    # Only implement these if the broker supports GTT/trigger orders.

    @staticmethod
    def to_gtt_id(raw: dict[str, Any]) -> str:
        return str(raw["data"]["id"])

    @staticmethod
    def to_gtt_params(
        token: str, broker_symbol: str, exchange: str, req: PlaceGttRequest,
    ) -> dict[str, Any]:
        raise NotImplementedError("Implement if broker supports GTT")

    @staticmethod
    def to_modify_gtt_params(
        token: str, broker_symbol: str, exchange: str, req: ModifyGttRequest,
    ) -> dict[str, Any]:
        raise NotImplementedError("Implement if broker supports GTT")

    @staticmethod
    def to_gtt(raw: dict[str, Any]) -> Gtt:
        raise NotImplementedError("Implement if broker supports GTT")

    # ---------------------------------------------------------------- Errors

    @staticmethod
    def parse_error(raw: dict[str, Any]) -> TTConnectError:
        """Map broker error envelope to canonical exception types."""
        code = raw.get("errorCode", "")
        message = raw.get("message", raw.get("errorMessage", "Unknown error"))
        exc_class = ERROR_MAP.get(code, BrokerError)
        return exc_class(message, broker_code=code)
```

**The BrokerTransformer Protocol requires all these methods.** Even if the broker doesn't support something (like GTT), you must define the method — raise `NotImplementedError` or `UnsupportedFeatureError`.

---

## Step 8: `parser.py` — Instrument Master Parsing

Parse the broker's instrument list into the four canonical groups: indices, equities, futures, options. The `InstrumentManager` calls your `parse()` function via the adapter's `fetch_instruments()`.

```python
# tt_connect/brokers/dhan/parser.py

"""Dhan instrument master parser."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ParsedIndex:
    exchange: str          # "NSE" or "BSE"
    symbol: str            # canonical symbol — e.g. "NIFTY"
    broker_symbol: str     # broker's own symbol
    segment: str           # "INDICES"
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str      # broker's numeric token

@dataclass(frozen=True)
class ParsedEquity:
    exchange: str
    symbol: str
    broker_symbol: str
    segment: str
    name: str | None
    lot_size: int
    tick_size: float
    broker_token: str

@dataclass(frozen=True)
class ParsedFuture:
    exchange: str              # derivative exchange (NFO, BFO)
    symbol: str                # underlying canonical name
    broker_symbol: str
    segment: str
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    underlying_exchange: str   # NSE for NFO, BSE for BFO

@dataclass(frozen=True)
class ParsedOption:
    exchange: str
    symbol: str
    broker_symbol: str
    segment: str
    lot_size: int
    tick_size: float
    broker_token: str
    expiry: date
    strike: float
    option_type: str           # "CE" or "PE"
    underlying_exchange: str

@dataclass
class ParsedInstruments:
    """Container for all parsed instrument groups."""
    indices:  list[ParsedIndex]  = field(default_factory=list)
    equities: list[ParsedEquity] = field(default_factory=list)
    futures:  list[ParsedFuture] = field(default_factory=list)
    options:  list[ParsedOption] = field(default_factory=list)


def parse(raw_data: list[dict] | str) -> ParsedInstruments:
    """Parse the broker's instrument master into ParsedInstruments.

    The input format depends on the broker — JSON list, CSV string, etc.
    """
    result = ParsedInstruments()

    for row in raw_data:
        segment = row.get("segment", "")
        inst_type = row.get("instrumentType", "")

        if segment == "INDICES":
            result.indices.append(ParsedIndex(
                exchange=row["exchange"],
                symbol=row["symbol"],
                broker_symbol=row["brokerSymbol"],
                segment="INDICES",
                name=row.get("name"),
                lot_size=int(row.get("lotSize", 1)),
                tick_size=float(row.get("tickSize", 0.05)),
                broker_token=str(row["securityId"]),
            ))
        elif inst_type == "EQUITY":
            result.equities.append(ParsedEquity(
                exchange=row["exchange"],
                symbol=row["symbol"],
                broker_symbol=row["symbol"],
                segment=segment,
                name=row.get("name"),
                lot_size=int(row.get("lotSize", 1)),
                tick_size=float(row.get("tickSize", 0.05)),
                broker_token=str(row["securityId"]),
            ))
        elif inst_type == "FUTIDX" or inst_type == "FUTSTK":
            result.futures.append(ParsedFuture(
                exchange=row["exchange"],
                symbol=row["underlyingSymbol"],
                broker_symbol=row["symbol"],
                segment=segment,
                lot_size=int(row["lotSize"]),
                tick_size=float(row["tickSize"]),
                broker_token=str(row["securityId"]),
                expiry=date.fromisoformat(row["expiry"]),
                underlying_exchange="NSE" if row["exchange"] == "NFO" else "BSE",
            ))
        elif inst_type in ("OPTIDX", "OPTSTK"):
            result.options.append(ParsedOption(
                exchange=row["exchange"],
                symbol=row["underlyingSymbol"],
                broker_symbol=row["symbol"],
                segment=segment,
                lot_size=int(row["lotSize"]),
                tick_size=float(row["tickSize"]),
                broker_token=str(row["securityId"]),
                expiry=date.fromisoformat(row["expiry"]),
                strike=float(row["strikePrice"]),
                option_type="CE" if "CE" in row["symbol"] else "PE",
                underlying_exchange="NSE" if row["exchange"] == "NFO" else "BSE",
            ))

    return result
```

**Critical constraints:**

- `ParsedInstruments` must have exactly these four fields: `indices`, `equities`, `futures`, `options`.
- Each parsed type must have `exchange`, `symbol`, `broker_symbol`, `broker_token` at minimum.
- Futures and options must have `underlying_exchange` — this is how the instrument store resolves the FK to the underlying.
- The `symbol` field must be the **canonical** underlying name (e.g. `"NIFTY"`, `"RELIANCE"`), not the broker's derivative tradingsymbol.

---

## Step 9: `ws.py` — WebSocket Client (Optional)

If the broker supports real-time streaming, extend `BrokerWebSocket`. If not, skip this file — the base adapter already raises `UnsupportedFeatureError`.

```python
# tt_connect/brokers/dhan/ws.py

"""Dhan WebSocket client."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

from tt_connect.core.store.resolver import ResolvedInstrument
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.models import Tick
from tt_connect.core.adapter.ws import BrokerWebSocket, OnTick

logger = logging.getLogger(__name__)

WS_URL = "wss://api-feed.dhan.co"


class DhanWebSocket(BrokerWebSocket):
    """Dhan live market data WebSocket client."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token
        self._on_tick: OnTick | None = None
        self._closed = False
        self._ws: Any | None = None
        self._task: asyncio.Task[None] | None = None
        self._token_map: dict[str, Instrument] = {}

    async def subscribe(
        self,
        subscriptions: list[tuple[Instrument, ResolvedInstrument]],
        on_tick: OnTick,
    ) -> None:
        self._on_tick = on_tick
        for instrument, resolved in subscriptions:
            self._token_map[resolved.token] = instrument

        if self._task is None or self._task.done():
            self._closed = False
            self._task = asyncio.create_task(self._run())

    async def unsubscribe(self, instruments: list[Instrument]) -> None:
        tokens = [t for t, inst in self._token_map.items() if inst in instruments]
        for t in tokens:
            self._token_map.pop(t, None)

    async def close(self) -> None:
        self._closed = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        """Reconnect loop with backoff."""
        delay = 2.0
        while not self._closed:
            try:
                await self._connect_and_run()
                delay = 2.0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"Dhan WS error: {exc}",
                               extra={"event": "ws.error", "broker": "dhan"})
            if self._closed:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    async def _connect_and_run(self) -> None:
        """Connect, subscribe, and dispatch ticks."""
        async with websockets.connect(WS_URL) as ws:
            self._ws = ws
            # Send auth + subscribe messages per broker's protocol
            # Parse incoming messages into Tick models
            # Call self._on_tick(tick) for each
            pass
```

**Key rules:**

- Implement the 3 abstract methods: `subscribe()`, `unsubscribe()`, `close()`.
- The `subscribe()` callback receives `(Instrument, ResolvedInstrument)` pairs — map broker tokens to instruments.
- Emit canonical `Tick` models via the `on_tick` callback.
- Implement reconnection with exponential backoff.
- Use `logger = logging.getLogger(__name__)` for structured logging.

---

## Step 10: Write Tests

```
tests/unit/brokers/dhan/
├── __init__.py
├── test_config.py          # Config validation: valid, missing fields, mode checks
├── test_transformer.py     # Raw JSON → canonical model for each method
├── test_parser.py          # Instrument master parsing edge cases
└── test_ws.py              # WebSocket subscribe/unsubscribe/close
```

**Minimum test coverage:**

- Config: valid config, missing required fields, mode validation, extra field rejection.
- Transformer: one test per `to_*` method with realistic raw JSON fixtures.
- Parser: at least one index, equity, future, and option row.
- Error mapping: each error code maps to the correct exception class.

---

## Verification Checklist

After creating all files, verify:

```bash
# 1. All tests pass (your new tests + all existing tests)
python -m pytest tests/ -q

# 2. Lint passes
python -m ruff check tt_connect/

# 3. Type check passes
python -m mypy tt_connect/ --ignore-missing-imports

# 4. Auto-discovery works — your broker should appear in the registry
python -c "from tt_connect.core.adapter.base import BrokerAdapter; print(BrokerAdapter._registry)"
# Should print: {'zerodha': ..., 'angelone': ..., 'dhan': ...}

# 5. Config registry works
python -c "from tt_connect.core.models.config import BrokerConfig; print(BrokerConfig._registry)"
# Should print: {'zerodha': ..., 'angelone': ..., 'dhan': ...}
```

---

## Common Gotchas

| Gotcha                                                         | Solution                                                                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Broker returns nested `data` (e.g. `{"data": {"net": [...]}}`) | Flatten it in the adapter before returning — the core expects `raw["data"]` to be the payload directly |
| Broker uses different field names for buy/sell                 | Map in the transformer, not the adapter                                                                |
| Broker's instrument token is a string, not an int              | Always store as `str` in `broker_token` — the resolver handles it                                      |
| Broker doesn't support GTT                                     | Don't override the GTT methods — the base class raises `UnsupportedFeatureError`                       |
| Broker uses different order status strings                     | Build a `_ORDER_STATUS_MAP` dict in your transformer                                                   |
| Broker's auth headers change per request                       | Return dynamic headers in the `headers` property                                                       |
| Index symbols differ from underlying names on F&O              | Create an `INDEX_NAME_MAP` like Zerodha's parser does                                                  |

---

## Summary

| File              | Purpose               | Base class / Protocol          | Registration                       |
| ----------------- | --------------------- | ------------------------------ | ---------------------------------- |
| `__init__.py`     | Trigger registration  | —                              | Imports adapter + config           |
| `config.py`       | Credential validation | `BrokerConfig`                 | `__init_subclass__(broker_id=...)` |
| `capabilities.py` | Feature matrix        | `Capabilities` (dataclass)     | —                                  |
| `auth.py`         | Login flow            | `BaseAuth`                     | —                                  |
| `adapter.py`      | REST wiring           | `BrokerAdapter`                | `__init_subclass__(broker_id=...)` |
| `transformer.py`  | Data normalization    | `BrokerTransformer` (Protocol) | —                                  |
| `parser.py`       | Instrument parsing    | —                              | —                                  |
| `ws.py`           | Live streaming        | `BrokerWebSocket`              | —                                  |

**Total: 8 files. Zero edits outside `brokers/dhan/`. Zero edits to core.**
