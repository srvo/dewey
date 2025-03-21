"""Tests for the LLM exception classes.

This module tests the custom exception classes in the exceptions.py module.
"""

import unittest

from dewey.llm.exceptions import (
    InvalidPromptError,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)


class TestLLMExceptions(unittest.TestCase):
    """Test the LLM exception classes."""

    def test_llm_error_base_class(self):
        """Test the LLMError base class."""
        # Create an instance with a message
        error = LLMError("Base error message")
        
        # Check the error message
        self.assertEqual(str(error), "Base error message")
        
        # Check that it's an instance of both LLMError and Exception
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_invalid_prompt_error(self):
        """Test the InvalidPromptError class."""
        # Create an instance with a message
        error = InvalidPromptError("Invalid prompt")
        
        # Check the error message
        self.assertEqual(str(error), "Invalid prompt")
        
        # Check that it's an instance of appropriate classes
        self.assertIsInstance(error, InvalidPromptError)
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_llm_connection_error(self):
        """Test the LLMConnectionError class."""
        # Create an instance with a message
        error = LLMConnectionError("Failed to connect to LLM provider")
        
        # Check the error message
        self.assertEqual(str(error), "Failed to connect to LLM provider")
        
        # Check that it's an instance of appropriate classes
        self.assertIsInstance(error, LLMConnectionError)
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_llm_response_error(self):
        """Test the LLMResponseError class."""
        # Create an instance with a message
        error = LLMResponseError("Invalid response from LLM")
        
        # Check the error message
        self.assertEqual(str(error), "Invalid response from LLM")
        
        # Check that it's an instance of appropriate classes
        self.assertIsInstance(error, LLMResponseError)
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_llm_timeout_error(self):
        """Test the LLMTimeoutError class."""
        # Create an instance with a message
        error = LLMTimeoutError("Request timed out after 60 seconds")
        
        # Check the error message
        self.assertEqual(str(error), "Request timed out after 60 seconds")
        
        # Check that it's an instance of appropriate classes
        self.assertIsInstance(error, LLMTimeoutError)
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_llm_rate_limit_error(self):
        """Test the LLMRateLimitError class."""
        # Create an instance with a message
        error = LLMRateLimitError("Rate limit exceeded, try again later")
        
        # Check the error message
        self.assertEqual(str(error), "Rate limit exceeded, try again later")
        
        # Check that it's an instance of appropriate classes
        self.assertIsInstance(error, LLMRateLimitError)
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_llm_authentication_error(self):
        """Test the LLMAuthenticationError class."""
        # Create an instance with a message
        error = LLMAuthenticationError("Invalid API key")
        
        # Check the error message
        self.assertEqual(str(error), "Invalid API key")
        
        # Check that it's an instance of appropriate classes
        self.assertIsInstance(error, LLMAuthenticationError)
        self.assertIsInstance(error, LLMError)
        self.assertIsInstance(error, Exception)

    def test_exception_inheritance(self):
        """Test the exception inheritance hierarchy."""
        # Check that all exceptions inherit from LLMError
        self.assertTrue(issubclass(InvalidPromptError, LLMError))
        self.assertTrue(issubclass(LLMConnectionError, LLMError))
        self.assertTrue(issubclass(LLMResponseError, LLMError))
        self.assertTrue(issubclass(LLMTimeoutError, LLMError))
        self.assertTrue(issubclass(LLMRateLimitError, LLMError))
        self.assertTrue(issubclass(LLMAuthenticationError, LLMError))
        
        # Check that LLMError inherits from Exception
        self.assertTrue(issubclass(LLMError, Exception))


if __name__ == "__main__":
    unittest.main() 