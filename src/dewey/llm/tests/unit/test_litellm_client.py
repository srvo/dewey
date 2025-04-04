"""Unit tests for the LiteLLM client module."""

from unittest.mock import MagicMock, patch

import pytest

from dewey.llm.litellm_client import LiteLLMClient, LiteLLMConfig, Message


class TestLiteLLMConfig:
    """Tests for the LiteLLMConfig class."""

    def test_initialize_with_defaults(self) -> None:
        """Test initializing LiteLLMConfig with default values."""
        config = LiteLLMConfig()

        # Verify default values
        assert config.model == "gpt-3.5-turbo"
        assert config.timeout == 60
        assert config.max_retries == 3
        assert not config.cache

    def test_initialize_with_custom_values(self) -> None:
        """Test initializing LiteLLMConfig with custom values."""
        config = LiteLLMConfig(
            model="claude-3-opus",
            timeout=120,
            max_retries=5,
            cache=True,
            fallback_models=["gpt-4", "claude-3-sonnet"],
        )

        # Verify custom values
        assert config.model == "claude-3-opus"
        assert config.timeout == 120
        assert config.max_retries == 5
        assert config.cache
        assert "gpt-4" in config.fallback_models
        assert "claude-3-sonnet" in config.fallback_models


class TestMessage:
    """Tests for the Message class."""

    def test_message_initialization(self) -> None:
        """Test initializing a Message object."""
        # Create messages of different roles
        system_msg = Message(role="system", content="You are a helpful assistant.")
        user_msg = Message(role="user", content="Hello, can you help me?")
        assistant_msg = Message(role="assistant", content="Sure, I'd be happy to help!")
        tool_msg = Message(
            role="tool", content="Search result: Information found.", name="search_tool",
        )

        # Verify message properties
        assert system_msg.role == "system"
        assert system_msg.content == "You are a helpful assistant."
        assert system_msg.name is None

        assert user_msg.role == "user"
        assert user_msg.content == "Hello, can you help me?"

        assert assistant_msg.role == "assistant"
        assert assistant_msg.content == "Sure, I'd be happy to help!"

        assert tool_msg.role == "tool"
        assert tool_msg.content == "Search result: Information found."
        assert tool_msg.name == "search_tool"


class TestLiteLLMClient:
    """Tests for the LiteLLMClient class."""

    @pytest.fixture()
    def mock_litellm_completion(self) -> MagicMock:
        """Mock for litellm.completion."""
        with patch("litellm.completion") as mock_completion:
            # Create a mock response that mimics ModelResponse structure
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = {"content": "This is a mock response"}
            mock_completion.return_value = mock_response
            yield mock_completion

    @pytest.fixture()
    def client(self) -> LiteLLMClient:
        """Create a basic LiteLLMClient for testing."""
        config = LiteLLMConfig(model="gpt-3.5-turbo")
        with patch("dewey.llm.litellm_client.logger"):  # Mock the logger
            return LiteLLMClient(config=config)

    def test_initialize_client(self, client) -> None:
        """Test basic client initialization."""
        assert client.config.model == "gpt-3.5-turbo"
        assert client.config.timeout == 60

    def test_generate_completion(self) -> None:
        """Test the generate_completion method."""
        # Arrange
        with patch("dewey.llm.litellm_client.logger"):  # Mock the logger
            with patch("dewey.llm.litellm_client.completion") as mock_completion:
                with patch("dewey.llm.litellm_client.completion_cost") as mock_cost:
                    # Set up the mocks
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message = {
                        "content": "This is a mock response",
                    }
                    mock_completion.return_value = mock_response
                    mock_cost.return_value = 0.001

                    # Create a client with a mocked litellm
                    config = LiteLLMConfig(model="gpt-3.5-turbo")
                    client = LiteLLMClient(config=config)

                    # Prepare test data
                    messages = [
                        Message(role="system", content="You are a helpful assistant."),
                        Message(role="user", content="Hello, world!"),
                    ]

                    # Act
                    response = client.generate_completion(messages)

                    # Assert
                    mock_completion.assert_called_once()
                    assert response == mock_response
