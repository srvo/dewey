# Formatting failed: LLM generation failed: Gemini API error: Could not acquire rate limit slot for gemini-2.0-flash after 3 attempts
from __future__ import annotations


class EthifinxError(Exception):
    """Base exception for Ethifinx."""


class APIError(EthifinxError):
    """Base class for API-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class DatabaseError(EthifinxError):
    """Base class for database-related errors."""

    def __init__(self, message: str, query: str | None = None) -> None:
        self.query = query
        super().__init__(message)


class ConfigurationError(EthifinxError):
    """Raised when there are issues with configuration."""


class DataImportError(EthifinxError):
    """Exception raised for errors during data import."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class WorkflowExecutionError(EthifinxError):
    """Exception raised for errors during workflow execution."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
