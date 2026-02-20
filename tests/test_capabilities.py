"""
Unit tests for Capabilities.auth_modes and verify_auth_mode().

No real API calls — purely testing the capability declarations and
the enforcement logic.
"""

import pytest
from tt_connect.capabilities import Capabilities
from tt_connect.enums import Exchange, OrderType, ProductType, AuthMode
from tt_connect.exceptions import UnsupportedFeatureError
from tt_connect.adapters.zerodha.capabilities import ZERODHA_CAPABILITIES
from tt_connect.adapters.angelone.capabilities import ANGELONE_CAPABILITIES


# ---------------------------------------------------------------------------
# AuthMode enum
# ---------------------------------------------------------------------------

class TestAuthModeEnum:
    def test_values(self):
        assert AuthMode.MANUAL == "manual"
        assert AuthMode.AUTO   == "auto"

    def test_string_construction(self):
        assert AuthMode("manual") is AuthMode.MANUAL
        assert AuthMode("auto")   is AuthMode.AUTO

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AuthMode("token")


# ---------------------------------------------------------------------------
# Capabilities.verify_auth_mode — generic
# ---------------------------------------------------------------------------

def _make_caps(auth_modes: set[AuthMode]) -> Capabilities:
    return Capabilities(
        broker_id="test",
        segments=frozenset({Exchange.NSE}),
        order_types=frozenset({OrderType.MARKET}),
        product_types=frozenset({ProductType.CNC}),
        auth_modes=frozenset(auth_modes),
    )


class TestVerifyAuthMode:
    def test_supported_mode_does_not_raise(self):
        caps = _make_caps({AuthMode.MANUAL})
        caps.verify_auth_mode(AuthMode.MANUAL)   # must not raise

    def test_unsupported_mode_raises(self):
        caps = _make_caps({AuthMode.MANUAL})
        with pytest.raises(UnsupportedFeatureError):
            caps.verify_auth_mode(AuthMode.AUTO)

    def test_error_message_names_broker(self):
        caps = _make_caps({AuthMode.MANUAL})
        with pytest.raises(UnsupportedFeatureError, match="test"):
            caps.verify_auth_mode(AuthMode.AUTO)

    def test_error_message_names_rejected_mode(self):
        caps = _make_caps({AuthMode.MANUAL})
        with pytest.raises(UnsupportedFeatureError, match="auto"):
            caps.verify_auth_mode(AuthMode.AUTO)

    def test_error_message_lists_supported_modes(self):
        caps = _make_caps({AuthMode.MANUAL})
        with pytest.raises(UnsupportedFeatureError, match="manual"):
            caps.verify_auth_mode(AuthMode.AUTO)

    def test_both_modes_supported(self):
        caps = _make_caps({AuthMode.MANUAL, AuthMode.AUTO})
        caps.verify_auth_mode(AuthMode.MANUAL)   # must not raise
        caps.verify_auth_mode(AuthMode.AUTO)     # must not raise

    def test_empty_auth_modes_rejects_everything(self):
        caps = _make_caps(set())
        with pytest.raises(UnsupportedFeatureError):
            caps.verify_auth_mode(AuthMode.MANUAL)
        with pytest.raises(UnsupportedFeatureError):
            caps.verify_auth_mode(AuthMode.AUTO)


# ---------------------------------------------------------------------------
# Zerodha capabilities — manual only
# ---------------------------------------------------------------------------

class TestZerodhaAuthModes:
    def test_has_auth_modes_field(self):
        assert hasattr(ZERODHA_CAPABILITIES, "auth_modes")

    def test_supports_manual(self):
        assert AuthMode.MANUAL in ZERODHA_CAPABILITIES.auth_modes

    def test_does_not_support_auto(self):
        assert AuthMode.AUTO not in ZERODHA_CAPABILITIES.auth_modes

    def test_verify_manual_passes(self):
        ZERODHA_CAPABILITIES.verify_auth_mode(AuthMode.MANUAL)

    def test_verify_auto_raises(self):
        with pytest.raises(UnsupportedFeatureError):
            ZERODHA_CAPABILITIES.verify_auth_mode(AuthMode.AUTO)

    def test_verify_auto_error_mentions_manual_as_supported(self):
        with pytest.raises(UnsupportedFeatureError, match="manual"):
            ZERODHA_CAPABILITIES.verify_auth_mode(AuthMode.AUTO)


# ---------------------------------------------------------------------------
# AngelOne capabilities — both modes
# ---------------------------------------------------------------------------

class TestAngelOneAuthModes:
    def test_has_auth_modes_field(self):
        assert hasattr(ANGELONE_CAPABILITIES, "auth_modes")

    def test_supports_manual(self):
        assert AuthMode.MANUAL in ANGELONE_CAPABILITIES.auth_modes

    def test_supports_auto(self):
        assert AuthMode.AUTO in ANGELONE_CAPABILITIES.auth_modes

    def test_verify_manual_passes(self):
        ANGELONE_CAPABILITIES.verify_auth_mode(AuthMode.MANUAL)

    def test_verify_auto_passes(self):
        ANGELONE_CAPABILITIES.verify_auth_mode(AuthMode.AUTO)


# ---------------------------------------------------------------------------
# Cross-broker — auth mode symmetry
# ---------------------------------------------------------------------------

class TestAuthModeSymmetry:
    def test_zerodha_is_strict_subset_of_angelone(self):
        assert ZERODHA_CAPABILITIES.auth_modes < ANGELONE_CAPABILITIES.auth_modes

    def test_all_brokers_support_at_least_one_mode(self):
        for caps in [ZERODHA_CAPABILITIES, ANGELONE_CAPABILITIES]:
            assert len(caps.auth_modes) >= 1, f"{caps.broker_id} has no auth modes"

    def test_auth_modes_are_frozenset(self):
        assert isinstance(ZERODHA_CAPABILITIES.auth_modes, frozenset)
        assert isinstance(ANGELONE_CAPABILITIES.auth_modes, frozenset)
