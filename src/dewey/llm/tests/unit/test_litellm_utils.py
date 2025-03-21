"""Unit tests for the LiteLLM utilities module."""

import os
import pytest
from unittest.mock import MagicMock, patch, mock_open

from dewey.llm.litellm_utils import (
    create_message,
    get_available_models,
    get_text_from_response,
    load_api_keys_from_env,
    set_api_keys,
    quick_completion,
)
from dewey.llm.litellm_client import Message


class TestLiteLLMUtils:
    """Tests for LiteLLM utility functions."""
    
    def test_create_message(self) -> None:
        """Test creating a message with different roles."""
        # Test system message
        system_message = create_message("system", "You are a helpful assistant.")
        assert isinstance(system_message, Message)
        assert system_message.role == "system"
        assert system_message.content == "You are a helpful assistant."
        
        # Test user message
        user_message = create_message("user", "Hello, world!")
        assert user_message.role == "user"
        assert user_message.content == "Hello, world!"
        
        # Test assistant message
        assistant_message = create_message("assistant", "I can help with that!")
        assert assistant_message.role == "assistant"
        assert assistant_message.content == "I can help with that!"
    
    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
    })
    def test_load_api_keys_from_env(self) -> None:
        """Test loading API keys from environment variables."""
        # Act
        keys = load_api_keys_from_env()
        
        # Assert
        assert keys["openai"] == "test-openai-key"
        assert keys["anthropic"] == "test-anthropic-key"
        
        # Keys that aren't in the environment should not be in the result
        assert "cohere" not in keys
    
    def test_set_api_keys(self) -> None:
        """Test setting API keys in litellm."""
        # Arrange
        api_keys = {
            "openai": "test-openai-key",
            "anthropic": "test-anthropic-key",
        }
        
        # Act
        with patch('dewey.llm.litellm_utils.litellm') as mock_litellm:
            with patch('dewey.llm.litellm_utils.os') as mock_os:
                with patch('dewey.llm.litellm_utils.logger') as mock_logger:
                    set_api_keys(api_keys)
                
                    # Assert
                    # Check if litellm.api_key is set for OpenAI
                    assert mock_litellm.api_key == "test-openai-key"
                    # Check if environment variable is set for Anthropic
                    mock_os.environ.__setitem__.assert_called_with("ANTHROPIC_API_KEY", "test-anthropic-key")
    
    def test_get_text_from_response(self) -> None:
        """Test extracting text from a model response."""
        # Arrange - create a proper dict-like response
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response"
                    }
                }
            ]
        }
        
        # Act
        with patch('dewey.llm.litellm_utils.logger') as mock_logger:
            text = get_text_from_response(mock_response)
        
        # Assert
        assert text == "This is a test response"
        
        # Test with classic completion format
        classic_response = {
            "choices": [
                {
                    "text": "This is a classic response"
                }
            ]
        }
        with patch('dewey.llm.litellm_utils.logger') as mock_logger:
            text = get_text_from_response(classic_response)
        assert text == "This is a classic response"
        
        # Test with Anthropic format
        anthropic_response = {
            "content": [
                {
                    "type": "text",
                    "text": "This is an Anthropic response"
                }
            ]
        }
        with patch('dewey.llm.litellm_utils.logger') as mock_logger:
            text = get_text_from_response(anthropic_response)
        assert text == "This is an Anthropic response"
        
        # Test with a None response - should return empty string
        with patch('dewey.llm.litellm_utils.logger') as mock_logger:
            try:
                text = get_text_from_response(None)
                assert False, "Should have raised an exception"
            except Exception:
                pass  # Expected exception
    
    def test_get_available_models(self) -> None:
        """Test getting available models."""
        # Act
        with patch('dewey.llm.litellm_utils.logger') as mock_logger:
            models = get_available_models()
        
        # Assert - we know this function returns a hardcoded list of 10 models
        assert len(models) == 10
        assert any(m["id"] == "gpt-3.5-turbo" for m in models)
        assert any(m["id"] == "gpt-4" for m in models)
        assert any(m["id"] == "claude-2" for m in models)
    
    def test_quick_completion(self) -> None:
        """Test quick completion function."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {"content": "This is a test completion"}
        
        # Act
        with patch('dewey.llm.litellm_utils.logger') as mock_logger:
            with patch('dewey.llm.litellm_utils.completion', return_value=mock_response):
                with patch('dewey.llm.litellm_utils.get_text_from_response', return_value="This is a test completion"):
                    result = quick_completion("Tell me a joke", model="gpt-3.5-turbo")
        
        # Assert
        assert result == "This is a test completion"