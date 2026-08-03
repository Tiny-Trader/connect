"""Construction errors and reprs for public instrument types."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from tt_connect.enums import Exchange, OptionType
from tt_connect.exceptions import ConfigurationError
from tt_connect.instruments import Commodity, Currency, Equity, Future, Index, Option
from tt_connect.core.models.instruments import Instrument


@pytest.mark.parametrize(
    ("cls", "required_snippet", "example_snippet"),
    [
        (Index, "exchange and symbol", 'Index(exchange=Exchange.NSE, symbol="NIFTY")'),
        (Equity, "exchange and symbol", 'Equity(exchange=Exchange.NSE, symbol="RELIANCE")'),
        (Currency, "exchange and symbol", "Currency(exchange=Exchange.CDS"),
        (Commodity, "exchange and symbol", "Commodity(exchange=Exchange.MCX"),
        (Future, "exchange, symbol, and expiry", "Future(exchange=Exchange.NFO"),
        (
            Option,
            "exchange, symbol, expiry, strike, and option_type",
            "Option(exchange=Exchange.NFO",
        ),
    ],
)
def test_missing_fields_raise_configuration_error_with_example(
    cls: type,
    required_snippet: str,
    example_snippet: str,
) -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        cls()

    msg = str(exc_info.value)
    assert f"{cls.__name__} requires {required_snippet}" in msg
    assert "Example:" in msg
    assert example_snippet in msg
    assert exc_info.value.__cause__ is None


def test_missing_fields_do_not_raise_bare_pydantic_validation_error() -> None:
    with pytest.raises(ConfigurationError):
        Index()
    with pytest.raises(ConfigurationError):
        Option()


def test_invalid_field_type_still_wrapped() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        Equity(exchange=Exchange.NSE, symbol=123)  # type: ignore[arg-type]

    msg = str(exc_info.value)
    assert msg.startswith("Invalid Equity:")
    assert "Example:" in msg
    assert 'Equity(exchange=Exchange.NSE, symbol="RELIANCE")' in msg


def test_valid_construction_unchanged() -> None:
    idx = Index(exchange=Exchange.NSE, symbol="NIFTY")
    assert idx.exchange == Exchange.NSE
    assert idx.symbol == "NIFTY"

    fut = Future(exchange=Exchange.NFO, symbol="NIFTY", expiry=date(2026, 3, 27))
    assert fut.expiry == date(2026, 3, 27)

    opt = Option(
        exchange=Exchange.NFO,
        symbol="NIFTY",
        expiry=date(2026, 3, 27),
        strike=25000,
        option_type=OptionType.CE,
    )
    assert opt.strike == 25000
    assert opt.option_type == OptionType.CE


def test_compact_repr() -> None:
    assert repr(Index(exchange=Exchange.NSE, symbol="NIFTY")) == "Index(NSE:NIFTY)"
    assert repr(Equity(exchange=Exchange.NSE, symbol="RELIANCE")) == "Equity(NSE:RELIANCE)"
    assert (
        repr(Future(exchange=Exchange.NFO, symbol="NIFTY", expiry=date(2026, 3, 27)))
        == "Future(NFO:NIFTY 2026-03-27)"
    )
    assert (
        repr(
            Option(
                exchange=Exchange.NFO,
                symbol="NIFTY",
                expiry=date(2026, 3, 27),
                strike=25000.0,
                option_type=OptionType.CE,
            )
        )
        == "Option(NFO:NIFTY 25000 CE 2026-03-27)"
    )


def test_base_instrument_also_wrapped() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        Instrument()
    assert "Instrument requires exchange and symbol" in str(exc_info.value)


def test_unrelated_models_still_use_pydantic_validation_error() -> None:
    """Instrument wrapping must not change other Pydantic models."""
    from tt_connect.core.models import Profile

    with pytest.raises(ValidationError):
        Profile(client_id="ZZ0001")  # missing name, email
