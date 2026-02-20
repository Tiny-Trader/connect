from tt_connect.models import Profile, Fund, Holding, Position, Order, Tick
from tt_connect.enums import Side, ProductType, OrderType, OrderStatus
from tt_connect.exceptions import (
    TTConnectError, AuthenticationError, OrderError,
    InvalidOrderError, InsufficientFundsError, BrokerError,
)

# AngelOne Error Codes (Example - based on SmartAPI docs)
# AG8001: Invalid Credentials
# AB1001: Invalid Token
ERROR_MAP: dict[str, type[TTConnectError]] = {
    "AG8001": AuthenticationError,
    "AB1001": AuthenticationError,
    "AB1008": AuthenticationError, # Invalid Session
}

class AngelOneTransformer:

    # --- Outgoing ---

    @staticmethod
    def to_order_params(instrument_token: str, qty: int, side: Side,
                        product: ProductType, order_type: OrderType,
                        price: float | None, trigger_price: float | None) -> dict:
        # TODO: Implement mapping later
        return {}

    # --- Incoming ---

    @staticmethod
    def to_profile(raw: dict) -> Profile:
        # TODO: Implement mapping later
        pass

    @staticmethod
    def to_fund(raw: dict) -> Fund:
        # TODO: Implement mapping later
        pass

    @staticmethod
    def to_order(raw: dict, instrument) -> Order:
        # TODO: Implement mapping later
        pass

    # --- Errors ---

    @staticmethod
    def parse_error(raw: dict) -> TTConnectError:
        code = raw.get("errorcode", "")
        message = raw.get("message", "Unknown error")
        exc_class = ERROR_MAP.get(code, BrokerError)
        return exc_class(message, broker_code=code)
