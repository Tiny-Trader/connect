from tt_connect.capabilities import Capabilities
from tt_connect.enums import Exchange, OrderType, ProductType, AuthMode

# TODO: Verify AngelOne's full capability matrix
ANGELONE_CAPABILITIES = Capabilities(
    broker_id="angelone",
    segments=frozenset({Exchange.NSE, Exchange.BSE, Exchange.NFO, Exchange.CDS, Exchange.MCX}),
    order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.SL, OrderType.SL_M}),
    product_types=frozenset({ProductType.CNC, ProductType.MIS, ProductType.NRML}),
    auth_modes=frozenset({AuthMode.MANUAL, AuthMode.AUTO}),  # Supports both: TOTP auto-login + manual token
)
