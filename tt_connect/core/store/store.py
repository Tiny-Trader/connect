"""Standalone public interface for the local instrument cache.

This module exposes a thin sync/async wrapper over the read-only discovery
queries in ``queries.py``. It intentionally does **not** authenticate with a
broker and does **not** refresh instrument data from the network.

Design boundary:

- ``TTConnect`` / ``AsyncTTConnect`` own broker auth and daily cache refresh.
- ``InstrumentStore`` / ``AsyncInstrumentStore`` own local DB access only.

That split keeps the public API honest:

- use the main client when you need fresh broker-backed data
- use the store when you want fast local instrument discovery, metadata, and
  option-chain browsing

If the local DB has not been seeded yet, store initialization fails with a
clear error telling the caller to initialize the main client first.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future as ThreadFuture
from datetime import date
from typing import Any, Coroutine, TypeVar

from tt_connect.core.models.enums import Exchange, OnStale, OptionType
from tt_connect.core.models.instruments import (
    Equity,
    Index,
    Instrument,
    InstrumentInfo,
    OptionChain,
)
from tt_connect.core.store.manager import InstrumentManager

T = TypeVar("T")


class AsyncInstrumentStore:
    """Async read-only interface to the local instrument cache.

    The store never authenticates or refreshes data from the broker. Initialize
    ``TTConnect`` or ``AsyncTTConnect`` first when you need a fresh DB.
    """

    def __init__(self, broker: str) -> None:
        """Create a store bound to an existing per-broker local DB."""
        self._broker_id = broker
        self._manager = InstrumentManager(broker_id=broker, on_stale=OnStale.FAIL)
        self._queries = self._manager.queries

    async def init(self) -> None:
        """Open the existing DB and fail clearly if it has not been seeded."""
        await self._manager.open_existing()

    async def close(self) -> None:
        """Close the DB connection."""
        if self._manager._conn is not None:
            await self._manager._conn.close()
            self._manager._conn = None
            self._queries.bind(None)

    async def __aenter__(self) -> "AsyncInstrumentStore":
        """Open the local DB and return the initialized store."""
        await self.init()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Close the local DB when leaving an async context manager."""
        await self.close()

    async def list_instruments(
        self,
        instrument_type: type[Instrument] | None = None,
        exchange: Exchange | None = None,
        underlying: Instrument | None = None,
        expiry: date | None = None,
        option_type: OptionType | None = None,
        strike: float | None = None,
        strike_min: float | None = None,
        strike_max: float | None = None,
        has_derivatives: bool | None = None,
        limit: int | None = 100,
    ) -> list[Instrument]:
        """List instruments using strict canonical filters."""
        return await self._queries.list_instruments(
            instrument_type=instrument_type,
            exchange=exchange,
            underlying=underlying,
            expiry=expiry,
            option_type=option_type,
            strike=strike,
            strike_min=strike_min,
            strike_max=strike_max,
            has_derivatives=has_derivatives,
            limit=limit,
        )

    async def get_expiries(self, instrument: Instrument) -> list[date]:
        """Return all distinct expiry dates for an underlying."""
        return await self._queries.get_expiries(instrument)

    async def search(self, query: str, exchange: str | None = None) -> list[Equity | Index]:
        """Search underlyings by symbol substring."""
        return await self._queries.search_instruments(query, exchange)

    async def get_instrument_info(self, instrument: Instrument) -> InstrumentInfo:
        """Return metadata such as lot size, tick size, and segment."""
        return await self._queries.get_instrument_info(instrument)

    async def get_option_chain(self, underlying: Instrument, expiry: date) -> OptionChain:
        """Return the option chain for a single underlying and expiry."""
        return await self._queries.get_option_chain(underlying, expiry)

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute raw SQL against the local instrument DB and return all rows."""
        return await self._queries.execute(sql, params)


class InstrumentStore:
    """Synchronous wrapper over :class:`AsyncInstrumentStore`."""

    def __init__(self, broker: str) -> None:
        """Open the local DB in a background event-loop thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._async = AsyncInstrumentStore(broker)
        try:
            self._run(self._async.init())
        except Exception:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()
            self._loop.close()
            raise

    def _run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine on the internal loop and block for the result."""
        fut: ThreadFuture[T] = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def close(self) -> None:
        """Close the DB connection and stop the internal event-loop thread."""
        self._run(self._async.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()

    def __enter__(self) -> "InstrumentStore":
        """Return the initialized sync store."""
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Close the store when leaving a sync context manager."""
        self.close()

    def list_instruments(
        self,
        instrument_type: type[Instrument] | None = None,
        exchange: Exchange | None = None,
        underlying: Instrument | None = None,
        expiry: date | None = None,
        option_type: OptionType | None = None,
        strike: float | None = None,
        strike_min: float | None = None,
        strike_max: float | None = None,
        has_derivatives: bool | None = None,
        limit: int | None = 100,
    ) -> list[Instrument]:
        """List instruments using strict canonical filters."""
        return self._run(
            self._async.list_instruments(
                instrument_type=instrument_type,
                exchange=exchange,
                underlying=underlying,
                expiry=expiry,
                option_type=option_type,
                strike=strike,
                strike_min=strike_min,
                strike_max=strike_max,
                has_derivatives=has_derivatives,
                limit=limit,
            )
        )

    def get_expiries(self, instrument: Instrument) -> list[date]:
        """Return all distinct expiry dates for an underlying."""
        return self._run(self._async.get_expiries(instrument))

    def search(self, query: str, exchange: str | None = None) -> list[Equity | Index]:
        """Search underlyings by symbol substring."""
        return self._run(self._async.search(query, exchange))

    def get_instrument_info(self, instrument: Instrument) -> InstrumentInfo:
        """Return metadata such as lot size, tick size, and segment."""
        return self._run(self._async.get_instrument_info(instrument))

    def get_option_chain(self, underlying: Instrument, expiry: date) -> OptionChain:
        """Return the option chain for a single underlying and expiry."""
        return self._run(self._async.get_option_chain(underlying, expiry))

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute raw SQL against the local instrument DB and return all rows."""
        return self._run(self._async.execute(sql, params))
