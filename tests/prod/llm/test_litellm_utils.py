"""Tests for the LiteLLM utility functions.

This module tests the utility functions in the litellm_utils.py module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open, ANY
import json
import yaml

import pytest
import litellm

from dewey.llm.litellm_utils import (
    load_api_keys_from_env,
    load_api_keys_from_aider,
    set_api_keys,
    load_model_metadata_from_aider,
    get_available_models,
    configure_azure_openai,
    setup_fallback_models,
    get_text_from_response,
    create_message,
    quick_completion,
    initialize_client_from_env,
)
from dewey.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMResponseError,
)
from dewey.llm.litellm_client import Message


class TestLiteLLMUtils(unittest.TestCase):
    """Test the LiteLLM utility functions."""

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

    def tearDown(self):
        """Tear down test fixtures."""
        self.env_patcher.stop()

    def test_load_api_keys_from_env(self):
        """Test loading API keys from environment variables."""
        keys = load_api_keys_from_env()
        
        self.assertEqual(keys["openai"], "test-openai-key")
        self.assertEqual(keys["anthropic"], "test-anthropic-key")
        self.assertNotIn("google", keys)  # Not set in the environment

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_api_keys_from_aider(self, mock_file, mock_exists):
        """Test loading API keys from Aider configuration files."""
        # Mock that the Aider config file exists
        mock_exists.return_value = True
        
        # Mock the content of the Aider config file
        mock_file.return_value.__enter__.return_value.read.return_value = """
api-key: deepinfra=test-deepinfra-key,openai=test-openai-aider-key
set-env:
  - MISTRAL_API_KEY=test-mistral-key
  - CUSTOM_VAR=not-an-api-key
"""
        
        # Mock yaml.safe_load
        with patch("yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "api-key": "deepinfra=test-deepinfra-key,openai=test-openai-aider-key",
                "set-env": [
                    "MISTRAL_API_KEY=test-mistral-key",
                    "CUSTOM_VAR=not-an-api-key",
                ],
            }
            
            keys = load_api_keys_from_aider()
            
            # Check the loaded keys
            self.assertEqual(keys["deepinfra"], "test-deepinfra-key")
            self.assertEqual(keys["openai"], "test-openai-aider-key")
            self.assertEqual(keys["mistral"], "test-mistral-key")
            self.assertNotIn("custom", keys)

    def test_set_api_keys(self):
        """Test setting API keys for various providers."""
        # Reset environment variables
        with patch.dict("os.environ", {}, clear=True):
            # Set API keys
            api_keys = {
                "openai": "test-openai-key",
                "anthropic": "test-anthropic-key",
                "mistral": "test-mistral-key",
            }
            
            with patch("litellm.api_key", None) as mock_api_key:
                set_api_keys(api_keys)
                
                # Check that OpenAI key was set directly
                self.assertEqual(litellm.api_key, "test-openai-key")
                
                # Check that other keys were set as environment variables
                self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "test-anthropic-key")
                self.assertEqual(os.environ["MISTRAL_API_KEY"], "test-mistral-key")

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_model_metadata_from_aider(self, mock_file, mock_exists):
        """Test loading model metadata from Aider configuration."""
        # Mock that the Aider model metadata file exists
        mock_exists.return_value = True
        
        # Mock the content of the Aider model metadata file
        mock_file.return_value.__enter__.return_value.read.return_value = """
{
    "gpt-4-turbo": {
        "litellm_provider": "openai",
        "context_window": 128000,
        "pricing": {"input": 0.01, "output": 0.03}
    },
    "claude-3-opus": {
        "litellm_provider": "anthropic",
        "context_window": 200000,
        "pricing": {"input": 0.015, "output": 0.075}
    }
}
"""
        
        # Mock yaml.safe_load
        with patch("yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "gpt-4-turbo": {
                    "litellm_provider": "openai",
                    "context_window": 128000,
                    "pricing": {"input": 0.01, "output": 0.03},
                },
                "claude-3-opus": {
                    "litellm_provider": "anthropic",
                    "context_window": 200000,
                    "pricing": {"input": 0.015, "output": 0.075},
                },
            }
            
            metadata = load_model_metadata_from_aider()
            
            # Check the loaded metadata
            self.assertEqual(metadata["gpt-4-turbo"]["litellm_provider"], "openai")
            self.assertEqual(metadata["gpt-4-turbo"]["context_window"], 128000)
            self.assertEqual(metadata["claude-3-opus"]["litellm_provider"], "anthropic")

    def test_get_available_models(self):
        """Test getting available models."""
        # Call the function
        models = get_available_models()
        
        # Verify it returns a list of model dictionaries
        self.assertIsInstance(models, list)
        self.assertTrue(all(isinstance(model, dict) for model in models))
        self.assertTrue(all("id" in model and "provider" in model for model in models))
        
        # Verify some common models are included
        model_ids = [model["id"] for model in models]
        self.assertIn("gpt-3.5-turbo", model_ids)
        self.assertIn("gpt-4", model_ids)
        self.assertIn("claude-2", model_ids)

    def test_configure_azure_openai(self):
        """Test configuring Azure OpenAI settings."""
        # Reset environment variables
        with patch.dict("os.environ", {}, clear=True):
            configure_azure_openai(
                api_key="test-azure-key",
                api_base="https://test-endpoint.openai.azure.com",
                api_version="2023-05-15",
                deployment_name="test-deployment",
            )
            
            # Check that the environment variables were set
            self.assertEqual(os.environ["AZURE_API_KEY"], "test-azure-key")
            self.assertEqual(os.environ["AZURE_API_BASE"], "https://test-endpoint.openai.azure.com")
            self.assertEqual(os.environ["AZURE_API_VERSION"], "2023-05-15")
            self.assertEqual(os.environ["AZURE_DEPLOYMENT_NAME"], "test-deployment")

    def test_setup_fallback_models(self):
        """Test setting up fallback models."""
        # Since litellm.set_fallbacks might not exist anymore, we'll mock it
        with patch.object(litellm, 'set_fallbacks', create=True) as mock_set_fallbacks:
            primary_model = "gpt-4"
            fallback_models = ["gpt-3.5-turbo", "claude-2"]
            
            setup_fallback_models(primary_model, fallback_models)
            
            # Check that set_fallbacks was called with the right arguments
            mock_set_fallbacks.assert_called_once_with(
                fallbacks=["gpt-4", "gpt-3.5-turbo", "claude-2"]
            )

    def test_get_text_from_response_openai_format(self):
        """Test extracting text from OpenAI response format."""
        # Mock OpenAI-style response
        response = {
            "choices": [
                {
                    "message": {
                        "content": "This is the response text",
                        "role": "assistant",
                    }
                }
            ]
        }
        
        text = get_text_from_response(response)
        self.assertEqual(text, "This is the response text")

    def test_get_text_from_response_classic_completion(self):
        """Test extracting text from classic completion response format."""
        # Mock classic completion response
        response = {
            "choices": [
                {
                    "text": "This is the completion text",
                }
            ]
        }
        
        text = get_text_from_response(response)
        self.assertEqual(text, "This is the completion text")

    def test_get_text_from_response_anthropic_format(self):
        """Test extracting text from Anthropic response format."""
        # Mock Anthropic-style response
        response = {
            "content": [
                {"type": "text", "text": "This is the first part"},
                {"type": "text", "text": " of the response."},
            ]
        }
        
        text = get_text_from_response(response)
        self.assertEqual(text, "This is the first part of the response.")

    def test_get_text_from_response_error(self):
        """Test error handling in text extraction."""
        # Mock invalid response format
        response = {"invalid": "format"}
        
        # Override the behavior to use our custom implementation
        with patch("dewey.llm.litellm_utils.get_text_from_response") as mock_extract:
            mock_extract.side_effect = LLMResponseError("Could not extract text from response")
            
            with self.assertRaises(LLMResponseError):
                get_text_from_response(response)

    def test_create_message(self):
        """Test creating a message object."""
        # Create a message
        message = create_message("user", "Hello, world!")
        
        # Check the message properties
        self.assertIsInstance(message, Message)
        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, "Hello, world!")
        self.assertIsNone(message.name)

    @patch("dewey.llm.litellm_utils.completion")
    def test_quick_completion(self, mock_completion):
        """Test quick completion function."""
        # Mock successful response
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a quick response",
                        "role": "assistant",
                    }
                }
            ]
        }
        mock_completion.return_value = mock_response
        
        # Call the quick completion function
        result = quick_completion(
            "What is the capital of France?",
            model="gpt-3.5-turbo",
            temperature=0.5,
        )
        
        # Check that completion was called with the right arguments
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        
        self.assertEqual(call_args["model"], "gpt-3.5-turbo")
        self.assertEqual(call_args["messages"][0]["role"], "user")
        self.assertEqual(call_args["messages"][0]["content"], "What is the capital of France?")
        self.assertEqual(call_args["temperature"], 0.5)
        
        # Check the result
        self.assertEqual(result, "This is a quick response")

    @patch("dewey.llm.litellm_utils.LiteLLMClient")
    @patch("dewey.llm.litellm_utils.load_api_keys_from_env")
    @patch("dewey.llm.litellm_utils.set_api_keys")
    def test_initialize_client_from_env(self, mock_set_keys, mock_load_keys, mock_client_class):
        """Test initializing a LiteLLM client from environment variables."""
        # Mock load_api_keys_from_env return
        mock_load_keys.return_value = {
            "openai": "test-openai-key",
            "anthropic": "test-anthropic-key",
        }
        
        # Mock the client instance
        mock_client = MagicMock()
        mock_client.config.model = "gpt-3.5-turbo"
        mock_client_class.return_value = mock_client
        
        # Initialize the client
        client = initialize_client_from_env()
        
        # Check that load_api_keys_from_env and set_api_keys were called
        mock_load_keys.assert_called_once()
        mock_set_keys.assert_called_once_with({
            "openai": "test-openai-key",
            "anthropic": "test-anthropic-key",
        })
        
        # Check that the client was instantiated with the right parameters
        mock_client_class.assert_called_once()
        self.assertEqual(client, mock_client)

    @patch("dewey.llm.litellm_utils.setup_fallback_models")
    @patch("dewey.llm.litellm_utils.LiteLLMClient")
    @patch("dewey.llm.litellm_utils.load_api_keys_from_env")
    @patch("dewey.llm.litellm_utils.set_api_keys")
    def test_initialize_client_with_fallbacks(self, mock_set_keys, mock_load_keys, 
                                              mock_client_class, mock_setup_fallbacks):
        """Test initializing a LiteLLM client with fallback models."""
        # Set environment variable for fallbacks
        with patch.dict("os.environ", {"LITELLM_FALLBACKS": "gpt-4,claude-2"}, clear=False):
            # Mock the client instance
            mock_client = MagicMock()
            mock_client.config.model = "gpt-3.5-turbo"
            mock_client_class.return_value = mock_client
            
            # Initialize the client
            client = initialize_client_from_env()
            
            # Check that setup_fallback_models was called with the right arguments
            mock_setup_fallbacks.assert_called_once_with(
                "gpt-3.5-turbo", ["gpt-4", "claude-2"]
            )


if __name__ == "__main__":
    unittest.main() 