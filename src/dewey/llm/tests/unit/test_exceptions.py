"""Unit tests for the LLM exceptions module."""

from dewey.core.exceptions import BaseException
from dewey.llm.exceptions import (
    InvalidPromptError,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)


class TestExceptions:
    """Tests for LLM exception classes."""

    def test_exception_inheritance(self) -> None:
        """Test that all exceptions inherit from appropriate base classes."""
        # All should inherit from BaseException
        assert issubclass(LLMError, BaseException)

        # All custom exceptions should inherit from LLMError
        assert issubclass(InvalidPromptError, LLMError)
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
        assert issubclass(LLMTimeoutError, LLMError)
        assert issubclass(LLMAuthenticationError, LLMError)

    def test_exception_instantiation(self) -> None:
        """Test that exceptions can be instantiated with messages."""
        test_msg = "Test error message"

        # Create instances with messages
        invalid_prompt = InvalidPromptError(test_msg)
        auth_error = LLMAuthenticationError(test_msg)
        conn_error = LLMConnectionError(test_msg)
        rate_limit = LLMRateLimitError(test_msg)
        response_error = LLMResponseError(test_msg)
        timeout = LLMTimeoutError(test_msg)

        # Verify messages are preserved
        assert str(invalid_prompt) == test_msg
        assert str(auth_error) == test_msg
        assert str(conn_error) == test_msg
        assert str(rate_limit) == test_msg
        assert str(response_error) == test_msg
        assert str(timeout) == test_msg
