import pytest
from src.dewey.llm.exceptions import LLMError


def test_llm_error_initialization_without_message():
    """Test LLMError initialization without a message."""
    error = LLMError()
    assert str(error) == ""  # Default message is empty string


def test_llm_error_initialization_with_message():
    """Test LLMError initialization with a message."""
    message = "Test error message"
    error = LLMError(message)
    assert str(error) == message


def test_llm_error_inheritance():
    """Test LLMError inherits from Exception."""
    error = LLMError()
    assert isinstance(error, Exception)
