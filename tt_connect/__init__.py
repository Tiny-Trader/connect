"""Public package entrypoint for tt-connect clients."""

from tt_connect.client import AsyncTTConnect
from tt_connect.models import ModifyOrderRequest, PlaceOrderRequest
from tt_connect.sync_client import TTConnect

# Import adapters to trigger auto-registration
import tt_connect.adapters.zerodha.adapter   # noqa: F401
import tt_connect.adapters.angelone.adapter  # noqa: F401

__all__ = ["TTConnect", "AsyncTTConnect", "PlaceOrderRequest", "ModifyOrderRequest"]
