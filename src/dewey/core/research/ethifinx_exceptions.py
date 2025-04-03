"""Ethifinx-specific exceptions."""


class EthifinxError(Exception):
    """
    Base exception for Ethifinx.
    """


class APIError(EthifinxError):
    """API-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class DatabaseError(EthifinxError):
    """Database-related errors."""

    def __init__(self, message: str, query: str | None = None) -> None:
        self.query = query
        super().__init__(message)


class ConfigurationError(EthifinxError):
    """Raised when there are issues with configuration."""


class DataImportError(EthifinxError):
    """Exception raised for errors during data import."""


class WorkflowExecutionError(EthifinxError):
    """Exception raised for errors during workflow execution."""
