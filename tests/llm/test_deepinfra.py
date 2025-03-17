"""Tests for DeepInfra API client."""

import os
import pytest
from unittest.mock import patch, MagicMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage, Choice
from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.exceptions import LLMError

@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch("dewey.llm.api_clients.deepinfra.OpenAI") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance

@pytest.fixture
def mock_env_api_key():
    """Mock environment variable for API key."""
    with patch.dict(os.environ, {"DEEPINFRA_API_KEY": "test_key"}):
        yield

class TestDeepInfraClient:
    """Test cases for DeepInfraClient."""

    def test_init_with_api_key(self, mock_openai):
        """Test initialization with provided API key."""
        client = DeepInfraClient(api_key="test_key")
        assert client.api_key == "test_key"
        mock_openai.assert_called_with(
            api_key="test_key",
            base_url="https://api.deepinfra.com/v1/openai"
        )

    def test_init_with_env_var(self, mock_openai, mock_env_api_key):
        """Test initialization using environment variable."""
        client = DeepInfraClient()
        assert client.api_key == "test_key"
        mock_openai.assert_called_with(
            api_key="test_key",
            base_url="https://api.deepinfra.com/v1/openai"
        )

    def test_init_without_api_key(self, mock_openai):
        """Test initialization without API key."""
        with patch.dict(os.environ, clear=True):
            with pytest.raises(LLMError, match="DeepInfra API key not found"):
                DeepInfraClient()

    def test_chat_completion_success(self, mock_openai):
        """Test successful chat completion."""
        # Create mock response
        mock_message = ChatCompletionMessage(
            content="Test response",
            role="assistant"
        )
        mock_choice = Choice(
            finish_reason="stop",
            index=0,
            message=mock_message
        )
        mock_completion = ChatCompletion(
            id="test_id",
            choices=[mock_choice],
            created=1234567890,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            object="chat.completion"
        )
        
        # Setup mock client
        mock_openai.chat.completions.create.return_value = mock_completion
        
        client = DeepInfraClient(api_key="test_key")
        response = client.chat_completion("Test prompt")
        
        assert response == "Test response"
        mock_openai.chat.completions.create.assert_called_with(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.7,
            max_tokens=1000
        )

    def test_chat_completion_with_system_message(self, mock_openai):
        """Test chat completion with system message."""
        mock_message = ChatCompletionMessage(
            content="Test response",
            role="assistant"
        )
        mock_choice = Choice(
            finish_reason="stop",
            index=0,
            message=mock_message
        )
        mock_completion = ChatCompletion(
            id="test_id",
            choices=[mock_choice],
            created=1234567890,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            object="chat.completion"
        )
        
        mock_openai.chat.completions.create.return_value = mock_completion
        
        client = DeepInfraClient(api_key="test_key")
        response = client.chat_completion(
            "Test prompt",
            system_message="You are a helpful assistant"
        )
        
        assert response == "Test response"
        mock_openai.chat.completions.create.assert_called_with(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Test prompt"}
            ],
            temperature=0.7,
            max_tokens=1000
        )

    def test_chat_completion_with_custom_params(self, mock_openai):
        """Test chat completion with custom parameters."""
        mock_message = ChatCompletionMessage(
            content="Test response",
            role="assistant"
        )
        mock_choice = Choice(
            finish_reason="stop",
            index=0,
            message=mock_message
        )
        mock_completion = ChatCompletion(
            id="test_id",
            choices=[mock_choice],
            created=1234567890,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            object="chat.completion"
        )
        
        mock_openai.chat.completions.create.return_value = mock_completion
        
        client = DeepInfraClient(api_key="test_key")
        response = client.chat_completion(
            "Test prompt",
            model="custom-model",
            temperature=0.5,
            max_tokens=500,
            top_p=0.9
        )
        
        assert response == "Test response"
        mock_openai.chat.completions.create.assert_called_with(
            model="custom-model",
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.5,
            max_tokens=500,
            top_p=0.9
        )

    def test_chat_completion_api_error(self, mock_openai):
        """Test chat completion when API call fails."""
        mock_openai.chat.completions.create.side_effect = Exception("API Error")
        
        client = DeepInfraClient(api_key="test_key")
        with pytest.raises(LLMError, match="DeepInfra API error: API Error"):
            client.chat_completion("Test prompt")

    def test_chat_completion_empty_response(self, mock_openai):
        """Test chat completion with empty response."""
        mock_message = ChatCompletionMessage(
            content="",
            role="assistant"
        )
        mock_choice = Choice(
            finish_reason="stop",
            index=0,
            message=mock_message
        )
        mock_completion = ChatCompletion(
            id="test_id",
            choices=[mock_choice],
            created=1234567890,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            object="chat.completion"
        )
        
        mock_openai.chat.completions.create.return_value = mock_completion
        
        client = DeepInfraClient(api_key="test_key")
        response = client.chat_completion("Test prompt")
        
        assert response == ""

    def test_stream_completion_not_implemented(self, mock_openai):
        """Test that stream_completion raises NotImplementedError."""
        client = DeepInfraClient(api_key="test_key")
        with pytest.raises(NotImplementedError, match="Streaming completion not implemented yet"):
            client.stream_completion() 