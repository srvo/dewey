"""Exceptions for the dewey LLM package."""

from dewey.core.exceptions import LLMError


class InvalidPromptError(LLMError):
    """Raised when a prompt is invalid."""


class LLMConnectionError(LLMError):
    """Raised when there's an issue connecting to the LLM provider."""


class LLMResponseError(LLMError):
    """Raised when there's an issue with the LLM response."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""


class LLMRateLimitError(LLMError):
    """Raised when the LLM rate limit is exceeded."""


class LLMAuthenticationError(LLMError):
    """Raised when there's an issue with LLM authentication."""
