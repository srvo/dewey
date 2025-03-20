from dewey.core.base_script import BaseScript

# Formatting failed: LLM generation failed: Gemini API error: Could not acquire rate limit slot for gemini-2.0-flash after 3 attempts
from __future__ import annotations

    def run(self) -> None:
        """
        Run the script.
        """
        # TODO: Implement script logic here
        raise NotImplementedError("The run method must be implemented")


class EthifinxError(BaseScript, BaseScriptException):
    """Base exception for Ethifinx."""


class APIError(BaseScriptEthifinxError):
    """Base class for API-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class DatabaseError(BaseScriptEthifinxError):
    """Base class for database-related errors."""

    def __init__(self, message: str, query: str | None = None) -> None:
        self.query = query
        super().__init__(message)


class ConfigurationError(BaseScriptEthifinxError):
    """Raised when there are issues with configuration."""


class DataImportError(BaseScriptEthifinxError):
    """Exception raised for errors during data import."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class WorkflowExecutionError(BaseScriptEthifinxError):
    """Exception raised for errors during workflow execution."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
