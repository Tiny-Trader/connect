"""BrokerTransformer Protocol — the contract each broker's transformer must fulfill."""

from __future__ import annotations

from typing import Any, Protocol

from tt_connect.core.exceptions import TTConnectError
from tt_connect.core.models.requests import (
    GetHistoricalRequest,
    ModifyGttRequest,
    ModifyOrderRequest,
    PlaceGttRequest,
    PlaceOrderRequest,
)
from tt_connect.core.models.responses import (
    Candle,
    Fund,
    Gtt,
    Holding,
    Order,
    Position,
    Profile,
    Tick,
    Trade,
)

JsonDict = dict[str, Any]


class BrokerTransformer(Protocol):
    """Transformer contract implemented by each broker adapter."""

    @staticmethod
    def parse_error(raw: JsonDict) -> TTConnectError: ...
    @staticmethod
    def to_order_id(raw: JsonDict) -> str: ...
    @staticmethod
    def to_close_position_params(pos_raw: JsonDict, qty: int, side: Any) -> JsonDict: ...
    @staticmethod
    def to_order_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceOrderRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_modify_params(req: ModifyOrderRequest) -> JsonDict: ...
    @staticmethod
    def to_gtt_id(raw: JsonDict) -> str: ...
    @staticmethod
    def to_gtt_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: PlaceGttRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_modify_gtt_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: ModifyGttRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_gtt(raw: JsonDict) -> Gtt: ...
    @staticmethod
    def to_profile(raw: JsonDict) -> Profile: ...
    @staticmethod
    def to_fund(raw: JsonDict) -> Fund: ...
    @staticmethod
    def to_holding(raw: JsonDict) -> Holding: ...
    @staticmethod
    def to_position(raw: JsonDict) -> Position: ...
    @staticmethod
    def to_trade(raw: JsonDict) -> Trade: ...
    @staticmethod
    def token_from_order(raw: JsonDict) -> str | None: ...
    @staticmethod
    def to_order(raw: JsonDict, instrument: Any = None) -> Order: ...
    @staticmethod
    def to_historical_params(
        token: str,
        broker_symbol: str,
        exchange: str,
        req: GetHistoricalRequest,
    ) -> JsonDict: ...
    @staticmethod
    def to_candles(rows: list[Any], instrument: Any) -> list[Candle]: ...
    @staticmethod
    def to_quote(raw: JsonDict, instrument: Any) -> Tick: ...
