from dataclasses import dataclass
from tt_connect.enums import Exchange, OrderType, ProductType, AuthMode
from tt_connect.exceptions import UnsupportedFeatureError
from tt_connect.instruments import Instrument, Index


@dataclass(frozen=True)
class Capabilities:
    broker_id: str
    segments: frozenset[Exchange]
    order_types: frozenset[OrderType]
    product_types: frozenset[ProductType]
    auth_modes: frozenset[AuthMode]

    def verify(
        self,
        instrument: Instrument,
        order_type: OrderType,
        product_type: ProductType,
    ) -> None:
        if isinstance(instrument, Index):
            raise UnsupportedFeatureError(
                "Indices are not tradeable. Use Equity, Future, or Option instead."
            )
        if instrument.exchange not in self.segments:
            raise UnsupportedFeatureError(
                f"{self.broker_id} does not support {instrument.exchange} segment"
            )
        if order_type not in self.order_types:
            raise UnsupportedFeatureError(
                f"{self.broker_id} does not support {order_type} order type"
            )
        if product_type not in self.product_types:
            raise UnsupportedFeatureError(
                f"{self.broker_id} does not support {product_type} product type"
            )

    def verify_auth_mode(self, mode: AuthMode) -> None:
        if mode not in self.auth_modes:
            supported = ", ".join(sorted(m.value for m in self.auth_modes))
            raise UnsupportedFeatureError(
                f"{self.broker_id} does not support auth_mode='{mode}'. "
                f"Supported: {supported}"
            )
