"""Integration tests for LiteLLM functionality.

Note: These tests require actual API keys to run.
To skip these tests when API keys are not available, use the
SKIP_INTEGRATION_TESTS environment variable.
"""

import os
from typing import Dict

import pytest

from dewey.llm.litellm_client import LiteLLMClient, LiteLLMConfig, Message
from dewey.llm.litellm_utils import load_api_keys_from_env, set_api_keys

# Skip all tests in this module if SKIP_INTEGRATION_TESTS is set
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION_TESTS") == "1", reason="Integration tests skipped"
)


@pytest.fixture(scope="module")
def api_keys() -> dict[str, str]:
    """Load API keys from environment variables."""
    keys = load_api_keys_from_env()
    if not keys:
        pytest.skip("No API keys found in environment")
    return keys


@pytest.fixture(scope="module")
def setup_litellm(api_keys) -> None:
    """Set up LiteLLM with API keys."""
    set_api_keys(api_keys)


class TestLiteLLMIntegration:
    """Integration tests for LiteLLM."""

    @pytest.fixture
    def openai_client(self, setup_litellm) -> LiteLLMClient:
        """Create a LiteLLMClient configured for OpenAI."""
        config = LiteLLMConfig(
            model_name="gpt-3.5-turbo", temperature=0.3, max_tokens=100
        )
        return LiteLLMClient(config=config)

    @pytest.mark.skipif(
        "OPENAI_API_KEY" not in os.environ, reason="OpenAI API key not found"
    )
    def test_openai_completion(self, openai_client) -> None:
        """Test a basic completion with OpenAI."""
        # Arrange
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Say 'Hello, world!'"),
        ]

        # Act
        response = openai_client.complete(messages)
        text = openai_client.get_text(response)

        # Assert
        assert response is not None
        assert text is not None
        assert len(text) > 0
        assert "hello" in text.lower()

    @pytest.fixture
    def anthropic_client(self, setup_litellm) -> LiteLLMClient:
        """Create a LiteLLMClient configured for Anthropic."""
        config = LiteLLMConfig(
            model_name="claude-3-haiku-20240307", temperature=0.3, max_tokens=100
        )
        return LiteLLMClient(config=config)

    @pytest.mark.skipif(
        "ANTHROPIC_API_KEY" not in os.environ, reason="Anthropic API key not found"
    )
    def test_anthropic_completion(self, anthropic_client) -> None:
        """Test a basic completion with Anthropic."""
        # Arrange
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Say 'Hello, world!'"),
        ]

        # Act
        response = anthropic_client.complete(messages)
        text = anthropic_client.get_text(response)

        # Assert
        assert response is not None
        assert text is not None
        assert len(text) > 0
        assert "hello" in text.lower()
