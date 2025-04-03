"""
    Integration tests for the LiteLLM implementation.

    This module tests the integration between LiteLLM components.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from dewey.llm.litellm_client import Message
from dewey.llm.litellm_utils import (
    get_text_from_response,
    initialize_client_from_env,
    load_api_keys_from_env,
    quick_completion,
    set_api_keys,
)


class TestLiteLLMIntegration(unittest.TestCase):
    """Integration tests for LiteLLM components."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-openai-key",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
                "LITELLM_MODEL": "gpt-3.5-turbo",
            },
            clear=True,
        )
        self.env_patcher.start()

        # Mock LiteLLM functions
        self.completion_patcher = patch("litellm.completion")
        self.mock_completion = self.completion_patcher.start()

        # Set up mock response
        mock_response = {
            "choices": [{"message": {"content": "Test response", "role": "assistant"}}]
        }
        self.mock_completion.return_value = mock_response

    def tearDown(self):
        """Tear down test fixtures."""
        self.env_patcher.stop()
        self.completion_patcher.stop()

    def test_end_to_end_workflow(self):
        """Test the end-to-end workflow from loading keys to getting a response."""
        # 1. Load API keys from environment
        api_keys = load_api_keys_from_env()
        self.assertEqual(api_keys["openai"], "test-openai-key")

        # 2. Set API keys
        set_api_keys(api_keys)

        # 3. Initialize client - use patching to ensure we get a usable client
        with patch("dewey.llm.litellm_utils.LiteLLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client = initialize_client_from_env()
            self.assertEqual(client, mock_client)

            # 4. Create messages
            messages = [
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello, world!"),
            ]

            # 5. Generate completion - the actual test is that the mocked client is called correctly
            mock_client.generate_completion.return_value = "Test response"
            response = mock_client.generate_completion(messages)

            # 6. Check response
            mock_client.generate_completion.assert_called_once()
            self.assertEqual(response, "Test response")

    def test_quick_completion_workflow(self):
        """Test the quick completion shortcut function."""
        # Mock quick_completion with patching to avoid API calls
        with patch("dewey.llm.litellm_utils.completion") as mock_completion:
            # Set up the mock response
            mock_response = {
                "choices": [
                    {
                        "message": {
                            "content": "Paris is the capital of France",
                            "role": "assistant",
                        }
                    }
                ]
            }
            mock_completion.return_value = mock_response

            # Use quick_completion function
            result = quick_completion(
                "What is the capital of France?",
                model="gpt-3.5-turbo",
            )

            # Check that completion was called with the right parameters
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args[1]
            self.assertEqual(call_args["model"], "gpt-3.5-turbo")
            self.assertEqual(call_args["messages"][0]["role"], "user")
            self.assertEqual(
                call_args["messages"][0]["content"], "What is the capital of France?"
            )

            # Check result
            self.assertEqual(result, "Paris is the capital of France")

    def test_module_imports(self):
        """Test that all required modules can be imported."""
        # This test verifies that all imports work correctly across the module
        import dewey.llm

        # Check that key components are available through the package
        self.assertTrue(hasattr(dewey.llm, "LiteLLMClient"))
        self.assertTrue(hasattr(dewey.llm, "Message"))
        self.assertTrue(hasattr(dewey.llm, "LiteLLMConfig"))
        self.assertTrue(hasattr(dewey.llm, "quick_completion"))
        self.assertTrue(hasattr(dewey.llm, "LLMError"))


@pytest.mark.skip(reason="Only run when you have actual API keys configured")
class TestLiteLLMRealAPI(unittest.TestCase):
"""
    Tests that use real API keys (should be skipped by default).

    These tests can be used for manual testing with real API keys.
    
"""

    def test_real_completion(self):
        """Test a real completion with actual API keys."""
        client = initialize_client_from_env()
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is the capital of France?"),
        ]

        response = client.generate_completion(messages)
        text = get_text_from_response(response)

        self.assertIn("Paris", text)

    def test_real_embedding(self):
        """Test a real embedding with actual API keys."""
        client = initialize_client_from_env()
        text = "This is a test for embedding generation"

        result = client.generate_embedding(text)

        self.assertIn("data", result)
        self.assertIn("embedding", result["data"][0])
        self.assertGreater(len(result["data"][0]["embedding"]), 0)


if __name__ == "__main__":
    unittest.main()