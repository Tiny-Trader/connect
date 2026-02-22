"""AngelOne request/response normalization helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tt_connect.enums import Exchange, Side, ProductType, OrderType, OrderStatus
from tt_connect.exceptions import (
    TTConnectError, AuthenticationError, OrderError, OrderNotFoundError,
    InvalidOrderError, InstrumentNotFoundError, BrokerError,
)
from tt_connect.instruments import Instrument
from tt_connect.models import Profile, Fund, Holding, Position, Order, Trade

# AngelOne error code → exception class  (source: SmartAPI official error list)
ERROR_MAP: dict[str, type[TTConnectError]] = {
    # --- Token / Session ---
    "AG8001": AuthenticationError,    # Invalid Token
    "AG8002": AuthenticationError,    # Token Expired
    "AG8003": AuthenticationError,    # Token Missing
    "AB8050": AuthenticationError,    # Invalid Refresh Token
    "AB8051": AuthenticationError,    # Refresh Token Expired
    "AB1010": AuthenticationError,    # AMX Session Expired
    "AB1011": AuthenticationError,    # Client Not Login
    # --- Credentials / Account ---
    "AB1000": AuthenticationError,    # Invalid Email Or Password
    "AB1001": AuthenticationError,    # Invalid Email
    "AB1002": AuthenticationError,    # Invalid Password Length
    "AB1005": AuthenticationError,    # User Type Must Be USER
    "AB1006": AuthenticationError,    # Client Is Blocked For Trading
    "AB1031": AuthenticationError,    # Old Password Mismatch
    "AB1032": AuthenticationError,    # User Not Found
    "AB1003": BrokerError,            # Client Already Exists
    # --- Orders ---
    "AB1008": InvalidOrderError,      # Invalid Order Variety
    "AB1012": InvalidOrderError,      # Invalid Product Type
    "AB1013": OrderNotFoundError,     # Order Not Found
    "AB4008": InvalidOrderError,      # ordertag length > 20 chars
    "AB2002": OrderError,             # ROBO order is blocked
    # --- Instruments / Portfolio ---
    "AB1009": InstrumentNotFoundError, # Symbol Not Found
    "AB1018": InstrumentNotFoundError, # Failed to Get Symbol Details
    "AB1014": BrokerError,            # Trade Not Found
    "AB1015": BrokerError,            # Holding Not Found
    "AB1016": BrokerError,            # Position Not Found
    "AB1017": BrokerError,            # Position Conversion Failed
    # --- Generic Server ---
    "AB1004": BrokerError,            # Something Went Wrong (generic)
    "AB1007": BrokerError,            # AMX Error
    "AB2000": BrokerError,            # Error Not Specified
    "AB2001": BrokerError,            # Internal Error
}

# AngelOne order status (lowercase) → canonical OrderStatus
_ORDER_STATUS_MAP: dict[str, OrderStatus] = {
    "complete":          OrderStatus.COMPLETE,
    "rejected":          OrderStatus.REJECTED,
    "cancelled":         OrderStatus.CANCELLED,
    "open":              OrderStatus.OPEN,
    "pending":           OrderStatus.PENDING,
    "trigger pending":   OrderStatus.PENDING,
    "amo req received":  OrderStatus.PENDING,
    "modified":          OrderStatus.OPEN,
    "open pending":      OrderStatus.PENDING,
    "cancel pending":    OrderStatus.OPEN,
    "modify pending":    OrderStatus.OPEN,
    "not modified":      OrderStatus.OPEN,
    "validation pending": OrderStatus.PENDING,
}

# AngelOne order type → canonical OrderType
_ORDER_TYPE_MAP: dict[str, OrderType] = {
    "MARKET":          OrderType.MARKET,
    "LIMIT":           OrderType.LIMIT,
    "STOPLOSS_LIMIT":  OrderType.SL,
    "STOPLOSS_MARKET": OrderType.SL_M,
}

# AngelOne product type → canonical ProductType
_PRODUCT_MAP: dict[str, ProductType] = {
    "CNC":          ProductType.CNC,
    "DELIVERY":     ProductType.CNC,   # trade book uses DELIVERY for CNC
    "MIS":          ProductType.MIS,
    "NRML":         ProductType.NRML,
    "CARRYFORWARD": ProductType.NRML,
    "MARGIN":       ProductType.NRML,
}

# AngelOne timestamp format: "16-Nov-2023 09:15:00"
_TS_FMT = "%d-%b-%Y %H:%M:%S"


def _parse_ts(raw: str | None) -> datetime | None:
    """Parse AngelOne timestamp string into datetime, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), _TS_FMT)
    except Exception:
        return None


def _f(val: Any) -> float:
    """Safely convert str/None to float."""
    try:
        return float(val) if val else 0.0
    except (TypeError, ValueError):
        return 0.0


def _i(val: Any) -> int:
    """Safely convert str/None to int."""
    try:
        return int(val) if val else 0
    except (TypeError, ValueError):
        return 0


class AngelOneTransformer:
    """Transforms AngelOne payloads to/from canonical tt-connect models."""

    # --- Outgoing ---

    @staticmethod
    def to_order_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        qty: int,
        side: Side,
        product: ProductType,
        order_type: OrderType,
        price: float | None,
        trigger_price: float | None,
    ) -> dict[str, Any]:
        """Build AngelOne order placement payload from canonical arguments."""
        params: dict[str, Any] = {
            "variety":         "NORMAL",
            "symboltoken":     token,
            "tradingsymbol":   broker_symbol,
            "exchange":        exchange,
            "transactiontype": side.value,
            "ordertype":       order_type.value,
            "producttype":     product.value,
            "duration":        "DAY",
            "quantity":        str(qty),
            "price":           str(price or 0),
            "squareoff":       "0",
            "stoploss":        "0",
        }
        if trigger_price:
            params["triggerprice"] = str(trigger_price)
        return params

    @staticmethod
    def to_order_id(raw: dict[str, Any]) -> str:
        """Extract order id from successful place/modify responses."""
        return str(raw["data"]["orderid"])

    @staticmethod
    def to_close_position_params(pos_raw: dict[str, Any], qty: int, side: Side) -> dict[str, Any]:
        """Build market-order payload used to offset an open position."""
        return {
            "variety":         "NORMAL",
            "symboltoken":     pos_raw.get("symboltoken", ""),
            "tradingsymbol":   pos_raw["tradingsymbol"],
            "exchange":        pos_raw["exchange"],
            "transactiontype": side.value,
            "ordertype":       "MARKET",
            "producttype":     pos_raw["producttype"],
            "duration":        "DAY",
            "quantity":        str(qty),
            "price":           "0",
            "squareoff":       "0",
            "stoploss":        "0",
        }

    # --- Incoming ---

    @staticmethod
    def to_profile(raw: dict[str, Any]) -> Profile:
        """Normalize profile payload."""
        return Profile(
            client_id=raw["clientcode"],
            name=raw["name"].strip(),
            email=raw.get("email", "") or "",
            phone=raw.get("mobileno") or None,
        )

    @staticmethod
    def to_fund(raw: dict[str, Any]) -> Fund:
        """Normalize funds/RMS payload."""
        # AngelOne returns all values as strings
        return Fund(
            available=_f(raw.get("availablecash")),
            used=_f(raw.get("utiliseddebits")),
            total=_f(raw.get("net")),
            collateral=_f(raw.get("collateral")),
            m2m_unrealized=_f(raw.get("m2munrealized")),
            m2m_realized=_f(raw.get("m2mrealized")),
        )

    @staticmethod
    def to_holding(raw: dict[str, Any]) -> Holding:
        """Normalize holdings row."""
        avg = _f(raw.get("averageprice"))
        ltp = _f(raw.get("ltp"))
        pnl = _f(raw.get("profitandloss"))
        pnl_pct = _f(raw.get("pnlpercentage"))
        # Strip -EQ suffix from symbol for canonical name
        symbol: str = (raw.get("tradingsymbol") or "").removesuffix("-EQ")
        return Holding(
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=symbol,
            ),
            qty=_i(raw.get("quantity")),
            avg_price=avg,
            ltp=ltp,
            pnl=pnl,
            pnl_percent=pnl_pct,
        )

    @staticmethod
    def to_position(raw: dict[str, Any]) -> Position:
        """Normalize positions row."""
        net_qty = _i(raw.get("netqty"))
        # avg price: buy side for long, sell side for short
        if net_qty >= 0:
            avg = _f(raw.get("totalbuyavgprice") or raw.get("cfbuyavgprice"))
        else:
            avg = _f(raw.get("totalsellav gprice") or raw.get("cfsellavgprice"))
        ltp = _f(raw.get("ltp"))
        pnl = _f(raw.get("urealised")) + _f(raw.get("realised"))
        symbol: str = (raw.get("tradingsymbol") or "").removesuffix("-EQ")
        return Position(
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=symbol,
            ),
            qty=net_qty,
            avg_price=avg,
            ltp=ltp,
            pnl=pnl,
            product=_PRODUCT_MAP.get(raw.get("producttype", ""), ProductType.NRML),
        )

    @staticmethod
    def to_order(raw: dict[str, Any], instrument: Instrument | None = None) -> Order:
        """Normalize order row with status/order/product mappings."""
        status_raw = (raw.get("status") or raw.get("orderstatus") or "").lower()
        status = _ORDER_STATUS_MAP.get(status_raw, OrderStatus.PENDING)
        order_type = _ORDER_TYPE_MAP.get(raw.get("ordertype", ""), OrderType.MARKET)
        product = _PRODUCT_MAP.get(raw.get("producttype", ""), ProductType.NRML)
        return Order(
            id=raw["orderid"],
            instrument=instrument,
            side=Side(raw["transactiontype"]),
            qty=_i(raw.get("quantity")),
            filled_qty=_i(raw.get("filledshares")),
            product=product,
            order_type=order_type,
            status=status,
            price=_f(raw.get("price")) or None,
            trigger_price=_f(raw.get("triggerprice")) or None,
            avg_price=_f(raw.get("averageprice")) or None,
            timestamp=_parse_ts(raw.get("updatetime") or raw.get("exchtime")),
        )

    @staticmethod
    def to_trade(raw: dict[str, Any]) -> Trade:
        """Normalize trade row."""
        qty = _i(raw.get("fillsize"))
        price = _f(raw.get("fillprice"))
        symbol: str = (raw.get("tradingsymbol") or "").removesuffix("-EQ")
        return Trade(
            order_id=raw["orderid"],
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=symbol,
            ),
            side=Side(raw["transactiontype"]),
            qty=qty,
            avg_price=price,
            trade_value=round(qty * price, 2),
            product=_PRODUCT_MAP.get(raw.get("producttype", ""), ProductType.NRML),
            timestamp=_parse_ts(raw.get("filltime")),
        )

    # --- Errors ---

    @staticmethod
    def parse_error(raw: dict[str, Any]) -> TTConnectError:
        """Map AngelOne error envelope to canonical exception types."""
        code = raw.get("errorcode", "")
        message = raw.get("message", "Unknown error")
        exc_class = ERROR_MAP.get(code, BrokerError)
        return exc_class(message, broker_code=code)
