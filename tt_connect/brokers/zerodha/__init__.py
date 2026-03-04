"""Zerodha broker package — triggers adapter + config registration on import."""

import tt_connect.brokers.zerodha.adapter  # noqa: F401 — triggers BrokerAdapter registration
import tt_connect.brokers.zerodha.config   # noqa: F401 — triggers BrokerConfig registration
