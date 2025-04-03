"""Exceptions for the dewey core package."""


class BaseException(Exception):
    """Base exception for all Dewey-specific exceptions."""

    pass


class ConfigurationError(BaseException):
    """Raised when there's an issue with the configuration."""

    pass


class LoggingError(BaseException):
    """Raised when there's an issue with the logging system."""

    pass


class DatabaseConnectionError(BaseException):
    """Raised when there's an issue with the database connection."""

    pass


class DatabaseQueryError(BaseException):
    """Raised when there's an issue with a database query."""

    pass


class LLMError(BaseException):
    """Raised when there's an issue with the LLM interaction."""

    pass


class APIError(BaseException):
    """Raised when there's an issue with an API call."""

    pass
