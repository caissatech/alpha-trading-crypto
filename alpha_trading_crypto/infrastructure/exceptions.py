"""Infrastructure exceptions."""


class InfrastructureError(Exception):
    """Base exception for infrastructure layer."""

    pass


class APIError(InfrastructureError):
    """API error."""

    def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None) -> None:
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data from API
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class NetworkError(InfrastructureError):
    """Network error."""

    pass


class AuthenticationError(APIError):
    """Authentication error."""

    pass


class RateLimitError(APIError):
    """Rate limit error."""

    pass


class InvalidDataError(InfrastructureError):
    """Invalid data format error."""

    def __init__(self, message: str, data: dict | None = None) -> None:
        """
        Initialize invalid data error.

        Args:
            message: Error message
            data: Invalid data
        """
        super().__init__(message)
        self.data = data


class BacktestError(InfrastructureError):
    """Backtest error."""

    pass


class BlockchainError(InfrastructureError):
    """Blockchain error."""

    pass


class TransactionError(BlockchainError):
    """Transaction error."""

    pass

