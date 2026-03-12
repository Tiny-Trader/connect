"""Synchronous wrapper over AsyncTTConnect for use in scripts and notebooks."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future as ThreadFuture
from typing import Any, Coroutine, TypeVar

from datetime import date, datetime

from tt_connect.core.models.enums import CandleInterval, OrderType, ProductType, Side
from tt_connect.core.models.instruments import Equity, Future, Index, Instrument, Option
from tt_connect.core.models import Candle, Fund, Gtt, GttLeg, Holding, Order, Position, Profile, Tick, Trade

T = TypeVar("T")


class TTConnect:
    """Threaded synchronous wrapper over :class:`AsyncTTConnect`.

    Can be used as a context manager::

        with TTConnect("zerodha", config) as client:
            profile = client.get_profile()
    """

    def __init__(self, broker: str, config: dict[str, Any]) -> None:
        """Create a dedicated event loop thread and initialize the async client."""
        from tt_connect.core.client._async import AsyncTTConnect

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncTTConnect(broker, config)
        try:
            self._run(self._async.init())
        except Exception:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()
            self._loop.close()
            raise

    def _run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine on the internal loop and block for result."""
        fut: ThreadFuture[T] = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def close(self) -> None:
        """Close the async client and stop the internal event loop thread."""
        self._run(self._async.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()

    def __dir__(self) -> list[str]:
        return [
            name
            for name in super().__dir__()
            if not (name.startswith("_") and not name.startswith("__"))
        ]

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

    def place_order(
        self,
        instrument: Instrument,
        side: Side,
        qty: int,
        order_type: OrderType,
        product: ProductType,
        price: float | None = None,
        trigger_price: float | None = None,
        tag: str | None = None,
    ) -> str:
        return self._run(self._async.place_order(
            instrument=instrument, side=side, qty=qty,
            order_type=order_type, product=product,
            price=price, trigger_price=trigger_price, tag=tag,
        ))

    def modify_order(
        self,
        order_id: str,
        qty: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
        order_type: OrderType | None = None,
    ) -> None:
        self._run(self._async.modify_order(
            order_id=order_id, qty=qty, price=price,
            trigger_price=trigger_price, order_type=order_type,
        ))

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

    def place_gtt(
        self,
        instrument: Instrument,
        last_price: float,
        legs: list[GttLeg],
    ) -> str:
        return self._run(self._async.place_gtt(
            instrument=instrument, last_price=last_price, legs=legs,
        ))

    def modify_gtt(
        self,
        gtt_id: str,
        instrument: Instrument,
        last_price: float,
        legs: list[GttLeg],
    ) -> None:
        self._run(self._async.modify_gtt(
            gtt_id=gtt_id, instrument=instrument,
            last_price=last_price, legs=legs,
        ))

    def cancel_gtt(self, gtt_id: str) -> None:
        self._run(self._async.cancel_gtt(gtt_id))

    def get_gtt(self, gtt_id: str) -> Gtt:
        return self._run(self._async.get_gtt(gtt_id))

    def get_gtts(self) -> list[Gtt]:
        return self._run(self._async.get_gtts())

    def get_quotes(self, instruments: list[Instrument]) -> list[Tick]:
        return self._run(self._async.get_quotes(instruments))

    def get_historical(
        self,
        instrument: Instrument,
        interval: CandleInterval,
        from_date: datetime,
        to_date: datetime,
    ) -> list[Candle]:
        return self._run(self._async.get_historical(instrument, interval, from_date, to_date))

    def get_futures(self, instrument: Instrument) -> list[Future]:
        return self._run(self._async.get_futures(instrument))

    def get_options(
        self,
        instrument: Instrument,
        expiry: date | None = None,
    ) -> list[Option]:
        return self._run(self._async.get_options(instrument, expiry))

    def get_expiries(self, instrument: Instrument) -> list[date]:
        return self._run(self._async.get_expiries(instrument))

    def search_instruments(
        self,
        query: str,
        exchange: str | None = None,
    ) -> list[Equity | Index]:
        return self._run(self._async.search_instruments(query, exchange))
