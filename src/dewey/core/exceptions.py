"""Exceptions for the dewey core package."""


class BaseException(Exception):
    """
    Base exception for all Dewey-specific exceptions.
    """


class ConfigurationError(BaseException):
    """Raised when there's an issue with the configuration."""


class LoggingError(BaseException):
    """Raised when there's an issue with the logging system."""


class DatabaseConnectionError(BaseException):
    """Raised when there's an issue with the database connection."""


class DatabaseQueryError(BaseException):
    """Raised when there's an issue with a database query."""


class LLMError(BaseException):
    """Raised when there's an issue with the LLM interaction."""


class APIError(BaseException):
    """Raised when there's an issue with an API call."""
