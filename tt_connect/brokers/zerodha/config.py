"""Validated configuration for Zerodha Kite Connect."""

from tt_connect.core.models.config import BrokerConfig


class ZerodhaConfig(BrokerConfig, broker_id="zerodha"):
    """Validated configuration for Zerodha Kite Connect.

    Zerodha uses OAuth — obtain ``access_token`` via the Kite login URL
    and supply it here. Token expires at midnight IST each day.
    """

    api_key: str
    access_token: str
