"""Project-wide exception hierarchy for normalized error handling."""

class TTConnectError(Exception):
    """Base exception for all tt-connect errors."""

    retryable: bool = False

    def __init__(self, message: str, broker_code: str | None = None):
        """Create an error with optional raw broker error code metadata."""
        super().__init__(message)
        self.broker_code = broker_code


class AuthenticationError(TTConnectError):
    """Authentication/session failure."""

    retryable = False


class RateLimitError(TTConnectError):
    """Broker rate-limit rejection; caller may retry with backoff."""

    retryable = True


class InsufficientFundsError(TTConnectError):
    """Order rejected due to insufficient buying power/margin."""

    retryable = False


class InstrumentNotFoundError(TTConnectError):
    """Instrument could not be resolved in the local instrument master."""

    retryable = False


class UnsupportedFeatureError(TTConnectError):
    """Requested feature is not supported by the selected broker."""

    retryable = False


class BrokerError(TTConnectError):
    """Generic broker-originated failure."""

    retryable = False


class OrderError(TTConnectError):
    """Base class for order-specific failures."""

    retryable = False


class InvalidOrderError(OrderError):
    """Order payload/parameters failed broker validation."""

    retryable = False


class OrderNotFoundError(OrderError):
    """Referenced order id does not exist or is not accessible."""

    retryable = False
