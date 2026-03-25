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

    def __init__(
        self,
        message: str,
        broker_code: str | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message, broker_code=broker_code)
        self.retry_after = retry_after


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


class ConfigurationError(TTConnectError):
    """Invalid or incomplete broker configuration supplied at construction time."""

    retryable = False


class ClientNotConnectedError(TTConnectError):
    """Client must be connected before this operation. Call init() first."""

    retryable = False


class ClientClosedError(TTConnectError):
    """Client has been closed and cannot be reused."""

    retryable = False


class InstrumentManagerError(TTConnectError):
    """InstrumentManager not initialized. Call init() first."""

    retryable = False


class InstrumentStoreNotInitializedError(TTConnectError):
    """Instrument DB is unavailable for read-only store access."""

    retryable = False
