"""Synchronous wrapper over AsyncTTConnect for use in scripts and notebooks."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future as ThreadFuture
from typing import Any, Coroutine, TypeVar

from tt_connect.models import Fund, Holding, ModifyOrderRequest, Order, PlaceOrderRequest, Position, Profile, Trade

T = TypeVar("T")


class TTConnect:
    """Threaded synchronous wrapper over :class:`AsyncTTConnect`.

    Can be used as a context manager::

        with TTConnect("zerodha", config) as client:
            profile = client.get_profile()
    """

    def __init__(self, broker: str, config: dict[str, Any]) -> None:
        """Create a dedicated event loop thread and initialize the async client."""
        from tt_connect.client import AsyncTTConnect

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncTTConnect(broker, config)
        self._run(self._async.init())

    def _run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine on the internal loop and block for result."""
        fut: ThreadFuture[T] = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def close(self) -> None:
        """Close the async client and stop the internal event loop thread."""
        self._run(self._async.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()

    def __enter__(self) -> "TTConnect":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def get_profile(self) -> Profile:
        return self._run(self._async.get_profile())

    def get_funds(self) -> Fund:
        return self._run(self._async.get_funds())

    def get_holdings(self) -> list[Holding]:
        return self._run(self._async.get_holdings())

    def get_positions(self) -> list[Position]:
        return self._run(self._async.get_positions())

    def get_trades(self) -> list[Trade]:
        return self._run(self._async.get_trades())

    def place_order(self, req: PlaceOrderRequest) -> str:
        return self._run(self._async.place_order(req))

    def modify_order(self, req: ModifyOrderRequest) -> None:
        self._run(self._async.modify_order(req))

    def cancel_order(self, order_id: str) -> None:
        self._run(self._async.cancel_order(order_id))

    def cancel_all_orders(self) -> tuple[list[str], list[str]]:
        return self._run(self._async.cancel_all_orders())

    def close_all_positions(self) -> tuple[list[str], list[str]]:
        return self._run(self._async.close_all_positions())

    def get_order(self, order_id: str) -> Order:
        return self._run(self._async.get_order(order_id))

    def get_orders(self) -> list[Order]:
        return self._run(self._async.get_orders())
