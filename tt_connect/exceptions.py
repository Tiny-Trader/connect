class TTConnectError(Exception):
    retryable: bool = False

    def __init__(self, message: str, broker_code: str | None = None):
        super().__init__(message)
        self.broker_code = broker_code


class AuthenticationError(TTConnectError):     retryable = False
class RateLimitError(TTConnectError):          retryable = True
class InsufficientFundsError(TTConnectError):  retryable = False
class InstrumentNotFoundError(TTConnectError): retryable = False
class UnsupportedFeatureError(TTConnectError): retryable = False
class BrokerError(TTConnectError):             retryable = False

class OrderError(TTConnectError):              retryable = False
class InvalidOrderError(OrderError):           retryable = False
class OrderNotFoundError(OrderError):          retryable = False
