class EthifinxError(Exception):
    """Base exception for Ethifinx."""

    pass


class APIError(EthifinxError):
    """Base class for API-related errors."""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class DatabaseError(EthifinxError):
    """Base class for database-related errors."""

    def __init__(self, message: str, query: str = None):
        self.query = query
        super().__init__(message)


class ConfigurationError(EthifinxError):
    """Raised when there are issues with configuration."""

    pass


class DataImportError(EthifinxError):
    """Exception raised for errors during data import."""

    def __init__(self, message: str):
        super().__init__(message)


class WorkflowExecutionError(EthifinxError):
    """Exception raised for errors during workflow execution."""

    def __init__(self, message: str):
        super().__init__(message)
