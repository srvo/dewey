"""Tests for the LLMHandler class."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from dewey.llm.llm_utils import LLMHandler, LLMError, validate_model_params
from dewey.llm.api_clients.gemini import GeminiClient
from dewey.llm.api_clients.deepinfra import DeepInfraClient

@pytest.fixture
def llm_config():
    """Fixture providing basic LLM configuration."""
    return {
        "client": "gemini",
        "api_key": "test_key",
        "deepinfra_api_key": "test_deepinfra_key",
        "default_model": "gemini-2.0-flash",
        "temperature": 0.7,
        "max_tokens": 1000
    }

@pytest.fixture
def mock_gemini_client():
    """Fixture providing a mocked GeminiClient."""
    with patch("dewey.llm.llm_utils.GeminiClient") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance

@pytest.fixture
def mock_deepinfra_client():
    """Fixture providing a mocked DeepInfraClient."""
    with patch("dewey.llm.llm_utils.DeepInfraClient") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance

class TestLLMHandler:
    """Test cases for LLMHandler class."""

    def test_init_gemini(self, llm_config, mock_gemini_client):
        """Test initialization with Gemini client."""
        handler = LLMHandler(llm_config)
        assert isinstance(handler.client, MagicMock)
        mock_gemini_client.assert_not_called()  # Client is created but not used yet

    def test_init_deepinfra(self, llm_config, mock_deepinfra_client):
        """Test initialization with DeepInfra client."""
        llm_config["client"] = "deepinfra"
        handler = LLMHandler(llm_config)
        assert isinstance(handler.client, MagicMock)
        mock_deepinfra_client.assert_not_called()  # Client is created but not used yet

    def test_init_invalid_client(self, llm_config):
        """Test initialization with invalid client type."""
        llm_config["client"] = "invalid"
        with pytest.raises(LLMError, match="Unsupported LLM client"):
            LLMHandler(llm_config)

    def test_clean_json_response(self, llm_config, mock_gemini_client):
        """Test JSON response cleaning."""
        handler = LLMHandler(llm_config)
        
        # Test markdown code block removal
        response = '```json\n{"key": "value"}\n```'
        assert handler._clean_json_response(response) == '{"key": "value"}'
        
        # Test simple code block removal
        response = '```{"key": "value"}```'
        assert handler._clean_json_response(response) == '{"key": "value"}'
        
        # Test clean JSON
        response = '{"key": "value"}'
        assert handler._clean_json_response(response) == '{"key": "value"}'

    def test_extract_json(self, llm_config, mock_gemini_client):
        """Test JSON content extraction."""
        handler = LLMHandler(llm_config)
        
        # Test object extraction
        text = 'Here is the JSON: {"key": "value"} and some extra text'
        assert handler._extract_json(text) == '{"key": "value"}'
        
        # Test array extraction
        text = 'Here is the array: ["item1", "item2"] and more text'
        assert handler._extract_json(text) == '["item1", "item2"]'
        
        # Test no JSON content
        text = "No JSON here"
        assert handler._extract_json(text) == "No JSON here"

    def test_parse_json_response(self, llm_config, mock_gemini_client):
        """Test JSON response parsing."""
        handler = LLMHandler(llm_config)
        
        # Test valid JSON
        response = '{"key": "value"}'
        assert handler.parse_json_response(response) == {"key": "value"}
        
        # Test invalid JSON with strict=True
        with pytest.raises(LLMError):
            handler.parse_json_response("invalid json", strict=True)
        
        # Test invalid JSON with strict=False
        response = 'Here is the JSON: {"key": "value"}'
        assert handler.parse_json_response(response, strict=False) == {"key": "value"}

    def test_generate_response_gemini(self, llm_config, mock_gemini_client):
        """Test response generation with Gemini client."""
        mock_gemini_client.generate_content.return_value.text = "Test response"
        
        handler = LLMHandler(llm_config)
        response = handler.generate_response("Test prompt")
        
        assert response == "Test response"
        mock_gemini_client.generate_content.assert_called_once()

    def test_generate_response_json(self, llm_config, mock_gemini_client):
        """Test JSON response generation."""
        json_response = '{"result": "success"}'
        mock_gemini_client.generate_content.return_value.text = json_response
        
        handler = LLMHandler(llm_config)
        response = handler.generate_response(
            "Test prompt",
            response_format={"type": "json_object"}
        )
        
        assert response == {"result": "success"}
        assert "JSON" in mock_gemini_client.generate_content.call_args[0][0]

    def test_generate_response_with_fallback(self, llm_config, mock_gemini_client, mock_deepinfra_client):
        """Test response generation with fallback model."""
        # Make primary model fail
        mock_gemini_client.generate_content.side_effect = Exception("Primary failed")
        
        # Setup fallback response
        mock_deepinfra_client.chat_completion.return_value = "Fallback response"
        
        handler = LLMHandler(llm_config)
        response = handler.generate_response(
            "Test prompt",
            fallback_model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        )
        
        assert response == "Fallback response"
        mock_gemini_client.generate_content.assert_called_once()
        mock_deepinfra_client.chat_completion.assert_called_once()

    def test_generate_response_both_fail(self, llm_config, mock_gemini_client, mock_deepinfra_client):
        """Test handling of both primary and fallback failures."""
        # Make both models fail
        mock_gemini_client.generate_content.side_effect = Exception("Primary failed")
        mock_deepinfra_client.chat_completion.side_effect = Exception("Fallback failed")
        
        handler = LLMHandler(llm_config)
        with pytest.raises(LLMError, match="Both primary and fallback LLMs failed"):
            handler.generate_response(
                "Test prompt",
                fallback_model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
            )

    def test_json_response_parsing(self, llm_config, mock_gemini_client):
        """Test JSON response parsing with various formats."""
        test_cases = [
            # Clean JSON
            ('{"key": "value"}', {"key": "value"}),
            # JSON with code blocks
            ('```json\n{"key": "value"}\n```', {"key": "value"}),
            # JSON with extra whitespace
            ('\n  {"key": "value"}  \n', {"key": "value"}),
            # Array JSON
            ('[1, 2, 3]', [1, 2, 3]),
        ]
        
        handler = LLMHandler(llm_config)
        for input_str, expected in test_cases:
            mock_gemini_client.generate_content.return_value.text = input_str
            response = handler.generate_response(
                "Test prompt",
                response_format={"type": "json_object"}
            )
            assert response == expected

    def test_json_extraction_non_strict(self, llm_config, mock_gemini_client):
        """Test JSON extraction in non-strict mode."""
        # Response with text before and after JSON
        response_text = 'Here is the response: {"key": "value"} End of response.'
        mock_gemini_client.generate_content.return_value.text = response_text
        
        handler = LLMHandler(llm_config)
        response = handler.generate_response(
            "Test prompt",
            response_format={"type": "json_object"},
            strict_json=False
        )
        
        assert response == {"key": "value"}

    def test_usage_stats_tracking(self, llm_config, mock_gemini_client):
        """Test tracking of usage statistics."""
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.usage.total_tokens = 50
        mock_gemini_client.generate_content.return_value = mock_response
        
        handler = LLMHandler(llm_config)
        handler.generate_response("Test prompt")
        
        assert handler.usage_stats["requests"] == 1
        assert handler.usage_stats["tokens"] == 50

    def test_client_specific_parameters(self, llm_config, mock_gemini_client, mock_deepinfra_client):
        """Test handling of client-specific parameters."""
        # Test Gemini parameters
        handler = LLMHandler(llm_config)
        handler.generate_response(
            "Test prompt",
            temperature=0.5,
            max_tokens=100
        )
        
        mock_gemini_client.generate_content.assert_called_with(
            "Test prompt",
            temperature=0.5,
            max_output_tokens=100,
            model="gemini-2.0-flash"
        )
        
        # Test DeepInfra parameters
        llm_config["client"] = "deepinfra"
        handler = LLMHandler(llm_config)
        handler.generate_response(
            "Test prompt",
            temperature=0.5,
            max_tokens=100
        )
        
        mock_deepinfra_client.chat_completion.assert_called_with(
            "Test prompt",
            temperature=0.5,
            max_tokens=100
        )

def test_validate_model_params():
    """Test validation of model parameters."""
    # Valid parameters
    validate_model_params({"temperature": 0.7, "max_tokens": 100})
    
    # Invalid temperature
    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        validate_model_params({"temperature": 3.0})
    
    # Invalid max_tokens
    with pytest.raises(ValueError, match="max_tokens must be positive integer"):
        validate_model_params({"max_tokens": -1}) 