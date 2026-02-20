from tt_connect.capabilities import Capabilities
from tt_connect.enums import Exchange, OrderType, ProductType, AuthMode

ZERODHA_CAPABILITIES = Capabilities(
    broker_id="zerodha",
    segments=frozenset({Exchange.NSE, Exchange.BSE, Exchange.NFO, Exchange.BFO, Exchange.CDS}),
    order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.SL, OrderType.SL_M}),
    product_types=frozenset({ProductType.CNC, ProductType.MIS, ProductType.NRML}),
    auth_modes=frozenset({AuthMode.MANUAL}),  # Zerodha OAuth requires human login; no automation
)
