import pytest
from unittest.mock import patch, MagicMock
import json
import logging

from dewey.llm.exceptions import LLMError
from dewey.llm.api_clients.deepinfra import DeepInfraClient


# Fixtures
@pytest.fixture
def setup_env(tmp_path, monkeypatch):
    """Sets up environment variables and temporary directories for testing."""
    monkeypatch.setenv("DEEPINFRA_API_KEY", "dummy_key")
    monkeypatch.setenv("DEWEY_PROJECT_ROOT", str(tmp_path))
    # Create a temporary .env file
    env_path = tmp_path / ".env"
    with open(env_path, "w") as f:
        f.write("DEEPINFRA_API_KEY=dummy_key")
    yield
    # Cleanup if needed


@pytest.fixture
def client(setup_env):
    """Provides a DeepInfraClient instance for testing."""
    return DeepInfraClient()


def test_initialization_without_api_key():
    """Test that initialization raises LLMError when no API key is found."""
    with pytest.raises(LLMError, match="DeepInfra API key not found"):
        with patch("dewey.config.load_config") as mock_load_config:
            mock_load_config.return_value = {
                "llm": {"providers": {"deepinfra": {"api_key": None}}}
            }
            DeepInfraClient()


def test_chat_completion_invalid_api_key():
    """Test error handling when API key is invalid (mocked response)."""
    with patch("openai.ChatCompletion") as mock_chat:
        mock_chat.completions.create.side_effect = Exception("Invalid API key")
        client = DeepInfraClient()
        with pytest.raises(LLMError, match="Invalid API key"):
            client.chat_completion("Test prompt")


def test_chat_completion_json_formatting():
    """Test JSON response formatting and cleanup."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='```json\n{"key": "value"}// comment\n```'))
    ]
    mock_response.usage = MagicMock(
        prompt_tokens=10, completion_tokens=5, total_tokens=15
    )

    with patch("openai.ChatCompletion") as mock_chat:
        mock_chat.completions.create.return_value = mock_response
        client = DeepInfraClient()
        result = client.chat_completion(
            "Test prompt", response_format={"type": "object"}
        )
        assert result == '{"key": "value"}'


def test_save_llm_output(tmp_path, monkeypatch):
    """Test saving LLM output to file."""
    monkeypatch.setenv("DEWEY_PROJECT_ROOT", str(tmp_path))
    client = DeepInfraClient()
    prompt = "Test prompt"
    response = "Test response"
    model = "test_model"
    metadata = {"test": "data"}

    client._save_llm_output(prompt, response, model, metadata)

    output_dir = tmp_path / "docs" / "llm_outputs"
    assert output_dir.exists()
    files = list(output_dir.glob("llm_output_*.json"))
    assert len(files) == 1

    with open(files[0], "r") as f:
        data = json.load(f)
        assert data["prompt"] == prompt
        assert data["response"] == response
        assert data["model"] == model
        assert data["metadata"] == metadata


def test_generate_content_alias():
    """Test that generate_content is an alias for chat_completion."""
    client = DeepInfraClient()
    with patch.object(client, "chat_completion") as mock_chat:
        mock_chat.return_value = "test"
        result = client.generate_content("Test prompt")
        mock_chat.assert_called_once_with(
            "Test prompt", model=None, temperature=0.7, max_tokens=1000, **{}
        )
        assert result == "test"


def test_rate_limit_error():
    """Test rate limit error handling."""
    with patch("openai.ChatCompletion") as mock_chat:
        mock_chat.completions.create.side_effect = Exception(
            "429 Client Error: Too Many Requests"
        )
        client = DeepInfraClient()
        with pytest.raises(LLMError, match="rate limit exceeded"):
            client.chat_completion("Test prompt")


def test_invalid_model():
    """Test model not found error handling."""
    with patch("openai.ChatCompletion") as mock_chat:
        mock_chat.completions.create.side_effect = Exception("404 Model not found")
        client = DeepInfraClient()
        with pytest.raises(LLMError, match="DeepInfra API error"):
            client.chat_completion("Test prompt", model="invalid_model")


def test_missing_model_fallback():
    """Test fallback models when primary model is unavailable."""
    with patch("openai.ChatCompletion") as mock_chat:
        mock_chat.completions.create.side_effect = [
            Exception("404 Model not found"),  # First model fails
            MagicMock(),  # Fallback succeeds
        ]
        client = DeepInfraClient()
        client.config["fallback_models"] = ["fallback_model"]
        client.chat_completion("Test prompt")
        assert mock_chat.completions.create.call_count == 2
        assert (
            mock_chat.completions.create.call_args_list[1].kwargs["model"]
            == "fallback_model"
        )


# Additional edge case tests
def test_empty_prompt():
    """Test empty prompt raises ValueError."""
    client = DeepInfraClient()
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        client.chat_completion("")


def test_max_tokens_zero():
    """Test max_tokens=0 returns empty string."""
    client = DeepInfraClient()
    with pytest.raises(ValueError, match="max_tokens must be >0"):
        client.chat_completion("Test prompt", max_tokens=0)


def test_temperature_out_of_range():
    """Test invalid temperature values raise ValueError."""
    client = DeepInfraClient()
    with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
        client.chat_completion("Test prompt", temperature=3.0)
