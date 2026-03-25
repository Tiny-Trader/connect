"""Zerodha request/response normalization helpers."""

import json as _json
from datetime import datetime
from typing import Any

from tt_connect.core.timezone import IST

from tt_connect.core.models import Candle, GetHistoricalRequest, Gtt, GttLeg, ModifyGttRequest, ModifyOrderRequest, PlaceGttRequest, PlaceOrderRequest, Profile, Fund, Holding, Position, Order, Tick, Trade, Margin
from tt_connect.core.models.instruments import Instrument
from tt_connect.core.models.enums import CandleInterval, Exchange, Side, ProductType, OrderType, OrderStatus
from tt_connect.core.exceptions import (
    TTConnectError, AuthenticationError, OrderError,
    InvalidOrderError, BrokerError,
)

def _parse_ts(raw: str | None) -> datetime | None:
    """Parse a Zerodha ISO timestamp into an IST-aware datetime."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        return dt.replace(tzinfo=IST) if dt.tzinfo is None else dt.astimezone(IST)
    except Exception:
        return None


ERROR_MAP: dict[str, type[TTConnectError]] = {
    "TokenException":      AuthenticationError,
    "UserException":       AuthenticationError,
    "OrderException":      OrderError,
    "InputException":      InvalidOrderError,
    "MarginException":     OrderError,
    "HoldingException":    OrderError,
    "NetworkException":    BrokerError,
    "DataException":       BrokerError,
    "GeneralException":    BrokerError,
}

# Zerodha statuses that don't map 1-to-1 to our OrderStatus enum
_ORDER_STATUS_MAP: dict[str, OrderStatus] = {
    "COMPLETE":                  OrderStatus.COMPLETE,
    "REJECTED":                  OrderStatus.REJECTED,
    "CANCELLED":                 OrderStatus.CANCELLED,
    "OPEN":                      OrderStatus.OPEN,
    "MODIFIED":                  OrderStatus.OPEN,
    "PUT ORDER REQ RECEIVED":    OrderStatus.PENDING,
    "VALIDATION PENDING":        OrderStatus.PENDING,
    "OPEN PENDING":              OrderStatus.PENDING,
    "MODIFY VALIDATION PENDING": OrderStatus.OPEN,
    "MODIFY PENDING":            OrderStatus.OPEN,
    "TRIGGER PENDING":           OrderStatus.PENDING,
    "CANCEL PENDING":            OrderStatus.OPEN,
    "AMO REQ RECEIVED":          OrderStatus.PENDING,
}


class ZerodhaTransformer:
    """Transforms Zerodha raw payloads to/from canonical tt-connect models."""

    # --- Outgoing ---

    @staticmethod
    def to_order_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceOrderRequest,
    ) -> dict[str, Any]:
        """Build Zerodha order placement payload from a PlaceOrderRequest."""
        params: dict[str, Any] = {
            "tradingsymbol":    broker_symbol,
            "exchange":         exchange,
            "transaction_type": req.side.value,
            "quantity":         req.qty,
            "product":          req.product.value,
            "order_type":       req.order_type.value,
            "validity":         "DAY",
        }
        if req.price:
            params["price"] = req.price
        if req.trigger_price:
            params["trigger_price"] = req.trigger_price
        # Zerodha `tag` is max 20 alphanumeric chars — strip dashes from UUID
        params["tag"] = req.tag.replace("-", "")[:20]
        return params

    @staticmethod
    def to_modify_params(req: ModifyOrderRequest) -> dict[str, Any]:
        """Build Zerodha order modification payload from a ModifyOrderRequest."""
        params: dict[str, Any] = {}
        if req.qty is not None:
            params["quantity"] = req.qty
        if req.price is not None:
            params["price"] = req.price
        if req.trigger_price is not None:
            params["trigger_price"] = req.trigger_price
        if req.order_type is not None:
            params["order_type"] = req.order_type.value
        return params

    @staticmethod
    def to_order_id(raw: dict[str, Any]) -> str:
        """Extract order id from successful place/modify responses."""
        return str(raw["data"]["order_id"])

    @staticmethod
    def to_gtt_id(raw: dict[str, Any]) -> str:
        """Extract GTT trigger_id from create/modify/delete responses."""
        return str(raw["data"]["trigger_id"])

    @staticmethod
    def _gtt_orders(broker_symbol: str, exchange: str, legs: list[GttLeg]) -> str:
        """Serialize the orders array for Zerodha GTT form params."""
        return _json.dumps([
            {
                "exchange":        exchange,
                "tradingsymbol":   broker_symbol,
                "transaction_type": leg.side.value,
                "quantity":        leg.qty,
                "order_type":      "LIMIT",
                "product":         leg.product.value,
                "price":           leg.price,
            }
            for leg in legs
        ])

    @staticmethod
    def to_gtt_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceGttRequest,
    ) -> dict[str, Any]:
        """Build Zerodha GTT create form params (sent as form-encoded data)."""
        if not (1 <= len(req.legs) <= 2):
            raise InvalidOrderError(
                f"Zerodha GTT supports 1 or 2 legs, got {len(req.legs)}"
            )
        gtt_type = "single" if len(req.legs) == 1 else "two-leg"
        condition = _json.dumps({
            "exchange":       exchange,
            "tradingsymbol":  broker_symbol,
            "trigger_values": [leg.trigger_price for leg in req.legs],
            "last_price":     req.last_price,
        })
        return {
            "type":      gtt_type,
            "condition": condition,
            "orders":    ZerodhaTransformer._gtt_orders(broker_symbol, exchange, req.legs),
        }

    @staticmethod
    def to_modify_gtt_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: ModifyGttRequest,
    ) -> dict[str, Any]:
        """Build Zerodha GTT modify form params (same shape as create)."""
        if not (1 <= len(req.legs) <= 2):
            raise InvalidOrderError(
                f"Zerodha GTT supports 1 or 2 legs, got {len(req.legs)}"
            )
        gtt_type = "single" if len(req.legs) == 1 else "two-leg"
        condition = _json.dumps({
            "exchange":       exchange,
            "tradingsymbol":  broker_symbol,
            "trigger_values": [leg.trigger_price for leg in req.legs],
            "last_price":     req.last_price,
        })
        return {
            "type":      gtt_type,
            "condition": condition,
            "orders":    ZerodhaTransformer._gtt_orders(broker_symbol, exchange, req.legs),
        }

    @staticmethod
    def to_gtt(raw: dict[str, Any]) -> Gtt:
        """Normalize a Zerodha GTT trigger record."""
        condition = raw.get("condition", {})
        orders    = raw.get("orders", [])
        trigger_values: list[float] = condition.get("trigger_values", [])
        legs = [
            GttLeg(
                trigger_price=trigger_values[i] if i < len(trigger_values) else 0.0,
                price=float(o.get("price", 0)),
                side=Side(o["transaction_type"]),
                qty=int(o.get("quantity", 0)),
                product=ProductType(o["product"]),
            )
            for i, o in enumerate(orders)
        ]
        return Gtt(
            gtt_id=str(raw["id"]),
            status=str(raw.get("status", "")),
            symbol=condition.get("tradingsymbol", ""),
            exchange=condition.get("exchange", ""),
            legs=legs,
        )

    @staticmethod
    def to_close_position_params(pos_raw: dict[str, Any], qty: int, side: Side) -> dict[str, Any]:
        """Build market-order payload used to offset an open position."""
        return {
            "tradingsymbol":    pos_raw["tradingsymbol"],
            "exchange":         pos_raw["exchange"],
            "transaction_type": side.value,
            "quantity":         qty,
            "product":          pos_raw["product"],
            "order_type":       "MARKET",
            "validity":         "DAY",
        }

    # --- Incoming ---

    @staticmethod
    def to_profile(raw: dict[str, Any]) -> Profile:
        """Normalize profile payload."""
        return Profile(
            client_id=raw["user_id"],
            name=raw["user_name"],
            email=raw["email"],
            phone=raw.get("mobile"),
        )

    @staticmethod
    def to_fund(raw: dict[str, Any]) -> Fund:
        """Normalize funds/margins payload."""
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
    def to_holding(raw: dict[str, Any]) -> Holding:
        """Normalize holding row and compute pnl percentage."""
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
    def to_position(raw: dict[str, Any]) -> Position:
        """Normalize net position row."""
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
    def to_trade(raw: dict[str, Any]) -> Trade:
        """Normalize trade-book row."""
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
            timestamp=_parse_ts(ts),
        )

    @staticmethod
    def token_from_order(raw: dict[str, Any]) -> str | None:
        """Extract the broker token from a raw order-book row."""
        tok = raw.get("instrument_token")
        return str(tok) if tok is not None else None

    @staticmethod
    def to_order(raw: dict[str, Any], instrument: Instrument | None = None) -> Order:
        """Normalize order-book row with status mapping."""
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
            timestamp=_parse_ts(ts),
        )

    _INTERVAL_MAP: dict[CandleInterval, str] = {
        CandleInterval.MINUTE_1:  "minute",
        CandleInterval.MINUTE_3:  "3minute",
        CandleInterval.MINUTE_5:  "5minute",
        CandleInterval.MINUTE_10: "10minute",
        CandleInterval.MINUTE_15: "15minute",
        CandleInterval.MINUTE_30: "30minute",
        CandleInterval.HOUR_1:    "60minute",
        CandleInterval.DAY:       "day",
    }

    @staticmethod
    def to_historical_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: GetHistoricalRequest,
    ) -> dict[str, Any]:
        """Build Zerodha historical candle query params."""
        interval = ZerodhaTransformer._INTERVAL_MAP[req.interval]
        params: dict[str, Any] = {
            "interval": interval,
            "from":     req.from_date.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "to":       req.to_date.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if req.include_oi:
            params["oi"] = "1"
        return params

    @staticmethod
    def to_candles(rows: list[Any], instrument: Instrument) -> list[Candle]:
        """Convert Zerodha candle rows to canonical Candle models.

        Each row: [timestamp_str, open, high, low, close, volume, oi?]
        """
        result: list[Candle] = []
        for row in rows:
            dt = datetime.fromisoformat(str(row[0]))
            ts = dt.replace(tzinfo=IST) if dt.tzinfo is None else dt.astimezone(IST)
            result.append(Candle(
                instrument=instrument,
                timestamp=ts,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=int(row[5]),
                oi=int(row[6]) if len(row) > 6 else None,
            ))
        return result

    @staticmethod
    def to_margin(raw: dict[str, Any]) -> Margin:
        """Normalize basket margin response."""
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

    @staticmethod
    def to_quote(raw: dict[str, Any], instrument: Instrument) -> Tick:
        """Normalize one Zerodha full-quote payload into a canonical Tick.

        bid/ask come from the first level of the market depth array.
        oi=0 is normalised to None (Zerodha returns 0 for equities).
        """
        ts_str = raw.get("timestamp") or raw.get("last_trade_time")
        ts = _parse_ts(ts_str)
        oi_raw = raw.get("oi")
        depth = raw.get("depth", {})
        buy_levels  = depth.get("buy", [])
        sell_levels = depth.get("sell", [])
        best_bid = float(buy_levels[0]["price"])  if buy_levels  else None
        best_ask = float(sell_levels[0]["price"]) if sell_levels else None
        return Tick(
            instrument=instrument,
            ltp=float(raw["last_price"]),
            volume=raw.get("volume"),
            oi=int(oi_raw) if oi_raw else None,
            bid=best_bid if best_bid else None,
            ask=best_ask if best_ask else None,
            timestamp=ts,
        )

    # --- Errors ---

    @staticmethod
    def parse_error(raw: dict[str, Any]) -> TTConnectError:
        """Map broker error envelope to canonical exception types."""
        code = raw.get("error_type", "")
        message = raw.get("message", "Unknown error")
        exc_class = ERROR_MAP.get(code, BrokerError)
        return exc_class(message, broker_code=code)
