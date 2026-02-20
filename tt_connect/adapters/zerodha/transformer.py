from datetime import datetime
from tt_connect.models import Profile, Fund, Holding, Position, Order, Trade, Margin, Tick
from tt_connect.instruments import Instrument
from tt_connect.enums import Exchange, Side, ProductType, OrderType, OrderStatus
from tt_connect.exceptions import (
    TTConnectError, AuthenticationError, OrderError,
    InvalidOrderError, InsufficientFundsError, BrokerError,
)

ERROR_MAP: dict[str, type[TTConnectError]] = {
    "TokenException":      AuthenticationError,
    "PermissionException": AuthenticationError,
    "OrderException":      OrderError,
    "InputException":      InvalidOrderError,
    "NetworkException":    BrokerError,
}

# Zerodha statuses that don't map 1-to-1 to our OrderStatus enum
_ORDER_STATUS_MAP: dict[str, OrderStatus] = {
    "COMPLETE":           OrderStatus.COMPLETE,
    "REJECTED":           OrderStatus.REJECTED,
    "CANCELLED":          OrderStatus.CANCELLED,
    "OPEN":               OrderStatus.OPEN,
    "TRIGGER PENDING":    OrderStatus.PENDING,
    "AMO REQ RECEIVED":   OrderStatus.PENDING,
    "MODIFY PENDING":     OrderStatus.OPEN,
    "OPEN PENDING":       OrderStatus.PENDING,
    "CANCEL PENDING":     OrderStatus.OPEN,
    "VALIDATION PENDING": OrderStatus.PENDING,
}


class ZerodhaTransformer:

    # --- Outgoing ---

    @staticmethod
    def to_order_params(instrument_token: str, qty: int, side: Side,
                        product: ProductType, order_type: OrderType,
                        price: float | None, trigger_price: float | None) -> dict:
        params = {
            "tradingsymbol": instrument_token,
            "transaction_type": side.value,
            "quantity": qty,
            "product": product.value,
            "order_type": order_type.value,
            "validity": "DAY",
        }
        if price:
            params["price"] = price
        if trigger_price:
            params["trigger_price"] = trigger_price
        return params

    # --- Incoming ---

    @staticmethod
    def to_profile(raw: dict) -> Profile:
        return Profile(
            client_id=raw["user_id"],
            name=raw["user_name"],
            email=raw["email"],
            phone=raw.get("mobile"),
        )

    @staticmethod
    def to_fund(raw: dict) -> Fund:
        equity = raw["equity"]
        return Fund(
            available=equity["available"]["live_balance"],
            used=equity["utilised"]["debits"],
            total=equity["net"],
            collateral=equity["available"].get("collateral", 0.0),
            m2m_unrealized=equity["utilised"].get("m2m_unrealised", 0.0),
            m2m_realized=equity["utilised"].get("m2m_realised", 0.0),
        )

    @staticmethod
    def to_holding(raw: dict) -> Holding:
        avg = raw["average_price"]
        ltp = raw["last_price"]
        pnl_pct = round((ltp - avg) / avg * 100, 2) if avg else 0.0
        return Holding(
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=raw["tradingsymbol"],
            ),
            qty=raw["quantity"],
            avg_price=avg,
            ltp=ltp,
            pnl=raw["pnl"],
            pnl_percent=pnl_pct,
        )

    @staticmethod
    def to_position(raw: dict) -> Position:
        return Position(
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=raw["tradingsymbol"],
            ),
            qty=raw["quantity"],
            avg_price=raw["average_price"],
            ltp=raw["last_price"],
            pnl=raw["pnl"],
            product=ProductType(raw["product"]),
        )

    @staticmethod
    def to_trade(raw: dict) -> Trade:
        ts = raw.get("fill_timestamp") or raw.get("order_timestamp")
        return Trade(
            order_id=raw["order_id"],
            instrument=Instrument(
                exchange=Exchange(raw["exchange"]),
                symbol=raw["tradingsymbol"],
            ),
            side=Side(raw["transaction_type"]),
            qty=raw["quantity"],
            avg_price=raw["average_price"],
            trade_value=round(raw["quantity"] * raw["average_price"], 2),
            product=ProductType(raw["product"]),
            timestamp=datetime.fromisoformat(ts) if ts else None,
        )

    @staticmethod
    def to_order(raw: dict, instrument=None) -> Order:
        status = _ORDER_STATUS_MAP.get(raw["status"], OrderStatus.PENDING)
        ts = raw.get("order_timestamp") or raw.get("exchange_timestamp")
        return Order(
            id=raw["order_id"],
            instrument=instrument,
            side=Side(raw["transaction_type"]),
            qty=raw["quantity"],
            filled_qty=raw["filled_quantity"],
            product=ProductType(raw["product"]),
            order_type=OrderType(raw["order_type"]),
            status=status,
            price=raw.get("price") or None,
            trigger_price=raw.get("trigger_price") or None,
            avg_price=raw.get("average_price") or None,
            timestamp=datetime.fromisoformat(ts) if ts else None,
        )

    @staticmethod
    def to_margin(raw: dict) -> Margin:
        initial = raw["initial"]
        final   = raw["final"]
        total   = initial["total"]
        final_t = final["total"]
        return Margin(
            total=total,
            span=initial.get("span", 0.0),
            exposure=initial.get("exposure", 0.0),
            option_premium=initial.get("option_premium", 0.0),
            final_total=final_t,
            benefit=round(total - final_t, 2),
        )

    # --- Errors ---

    @staticmethod
    def parse_error(raw: dict) -> TTConnectError:
        code = raw.get("error_type", "")
        message = raw.get("message", "Unknown error")
        exc_class = ERROR_MAP.get(code, BrokerError)
        return exc_class(message, broker_code=code)
