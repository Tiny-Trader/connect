"""Async-first unified broker client."""

from tt_connect.instruments_mixin import InstrumentsMixin
from tt_connect.lifecycle import LifecycleMixin
from tt_connect.orders import OrdersMixin
from tt_connect.portfolio import PortfolioMixin
from tt_connect.sync_client import TTConnect

__all__ = ["AsyncTTConnect", "TTConnect"]


class AsyncTTConnect(LifecycleMixin, PortfolioMixin, OrdersMixin, InstrumentsMixin):
    """Async-first public client for normalized broker operations.

    Lifecycle:
    1. Construct with broker id and config.
    2. Call :meth:`init` once before any read/write operation.
    3. Call :meth:`close` to release HTTP, DB, and WebSocket resources.

    Can also be used as an async context manager::

        async with AsyncTTConnect("zerodha", config) as client:
            profile = await client.get_profile()
    """
