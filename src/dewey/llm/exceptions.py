"""Exceptions for the dewey LLM package."""

from dewey.core.exceptions import BaseException, LLMError


class InvalidPromptError(LLMError):
    """Raised when a prompt is invalid."""
    pass


class LLMConnectionError(LLMError):
    """Raised when there's an issue connecting to the LLM provider."""
    pass


class LLMResponseError(LLMError):
    """Raised when there's an issue with the LLM response."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when the LLM rate limit is exceeded."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when there's an issue with LLM authentication."""
    pass
