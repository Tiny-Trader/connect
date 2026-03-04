"""AngelOne broker package — triggers adapter + config registration on import."""

import tt_connect.brokers.angelone.adapter  # noqa: F401 — triggers BrokerAdapter registration
import tt_connect.brokers.angelone.config   # noqa: F401 — triggers BrokerConfig registration
