"""Tests for the Gemini API client."""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from dewey.llm.api_clients.gemini import GeminiClient, RateLimiter, LLMError


@pytest.fixture
def mock_genai():
    """Fixture providing a mocked google.generativeai module."""
    with patch("dewey.llm.api_clients.gemini.genai") as mock:
        yield mock


@pytest.fixture
def gemini_config():
    """Fixture providing Gemini client configuration."""
    return {
        "api_key": "test_key",
        "default_model": "gemini-2.0-flash",
        "fallback_model": "gemini-2.0-flash-lite",
        "model_limits": {
            "gemini-2.0-flash": {
                "rpm": 15,
                "tpm": 1000000,
                "rpd": 1500,
                "min_request_interval": 5,
                "circuit_breaker_threshold": 3,
                "circuit_breaker_timeout": 120,
            }
        },
    }


@pytest.fixture
def rate_limiter():
    """Fixture providing a RateLimiter instance."""
    limiter = RateLimiter()
    # Reset all state for clean testing
    limiter.request_windows = {}
    limiter.daily_requests = {}
    limiter.daily_start_time = {}
    limiter.last_request_time = {}
    limiter.failure_counts = {}
    limiter.circuit_open_until = {}
    return limiter


class TestRateLimiter:
    """Test cases for RateLimiter class."""

    def test_configure(self, rate_limiter):
        """Test rate limiter configuration."""
        config = {
            "model_limits": {
                "test-model": {
                    "rpm": 10,
                    "tpm": 500000,
                    "rpd": 1000,
                    "min_request_interval": 3,
                }
            }
        }
        rate_limiter.configure(config)
        assert rate_limiter.MODEL_LIMITS["test-model"]["rpm"] == 10
        assert rate_limiter.MODEL_LIMITS["test-model"]["tpm"] == 500000

    def test_get_limits(self, rate_limiter):
        """Test getting rate limits for a model."""
        rpm, tpm, rpd, interval = rate_limiter._get_limits("gemini-2.0-flash")
        assert rpm == 15
        assert tpm == 1000000
        assert rpd == 1500
        assert interval == 5

    def test_check_limit_rpm_exceeded(self, rate_limiter):
        """Test RPM limit enforcement."""
        model = "gemini-2.0-flash"
        now = time.time()

        # Add requests just under a minute ago
        rate_limiter.request_windows[model] = [now - 50] * 15

        with pytest.raises(LLMError, match="Rate limit .* exceeded"):
            rate_limiter.check_limit(model, "test prompt")

    def test_check_limit_circuit_breaker(self, rate_limiter):
        """Test circuit breaker functionality."""
        model = "gemini-2.0-flash"
        now = time.time()

        # Record failures up to threshold
        for _ in range(3):
            rate_limiter._record_failure(model, now)

        with pytest.raises(LLMError, match="Circuit breaker open"):
            rate_limiter.check_limit(model, "test prompt")

    def test_clean_request_window(self, rate_limiter):
        """Test request window cleaning."""
        model = "gemini-2.0-flash"
        now = time.time()

        # Add mix of old and new requests
        rate_limiter.request_windows[model] = [
            now - 70,  # Should be removed (> 1 minute old)
            now - 30,  # Should stay
            now - 10,  # Should stay
        ]

        rate_limiter._clean_request_window(model, now)
        assert len(rate_limiter.request_windows[model]) == 2


class TestGeminiClient:
    """Test cases for GeminiClient class."""

    def test_init_with_api_key(self, mock_genai, gemini_config):
        """Test client initialization with provided API key."""
        client = GeminiClient(api_key="test_key", config=gemini_config)
        assert client.api_key == "test_key"
        mock_genai.configure.assert_called_with(api_key="test_key")

    def test_init_with_env_var(self, mock_genai):
        """Test client initialization using environment variable."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env_test_key"}):
            client = GeminiClient()
            assert client.api_key == "env_test_key"
            mock_genai.configure.assert_called_with(api_key="env_test_key")

    def test_init_without_api_key(self, mock_genai):
        """Test client initialization without API key."""
        with patch.dict(os.environ, clear=True):
            with pytest.raises(LLMError, match="Gemini API key not found"):
                GeminiClient()

    def test_get_model(self, mock_genai, gemini_config):
        """Test model instance retrieval and caching."""
        client = GeminiClient(api_key="test_key", config=gemini_config)

        # First call should create new model
        model1 = client._get_model("gemini-2.0-flash")
        assert model1 == mock_genai.GenerativeModel.return_value
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")

        # Second call should return cached model
        mock_genai.GenerativeModel.reset_mock()
        model2 = client._get_model("gemini-2.0-flash")
        assert model2 == model1
        mock_genai.GenerativeModel.assert_not_called()

    def test_generate_content_success(self, mock_genai, gemini_config):
        """Test successful content generation."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "Test response"
        mock_genai.GenerativeModel.return_value = mock_model

        client = GeminiClient(api_key="test_key", config=gemini_config)
        response = client.generate_content("Test prompt")

        assert response == "Test response"
        mock_model.generate_content.assert_called_once()

    def test_generate_content_with_fallback(self, mock_genai, gemini_config):
        """Test content generation with fallback model."""
        # Make primary model fail
        mock_primary = MagicMock()
        mock_primary.generate_content.side_effect = Exception("Primary failed")

        # Setup fallback model
        mock_fallback = MagicMock()
        mock_fallback.generate_content.return_value.text = "Fallback response"

        mock_genai.GenerativeModel.side_effect = [mock_primary, mock_fallback]

        client = GeminiClient(api_key="test_key", config=gemini_config)
        response = client.generate_content("Test prompt")

        assert response == "Fallback response"
        mock_primary.generate_content.assert_called_once()
        mock_fallback.generate_content.assert_called_once()

    def test_generate_content_rate_limit(self, mock_genai, gemini_config):
        """Test rate limit handling during content generation."""
        client = GeminiClient(api_key="test_key", config=gemini_config)

        # Fill up the rate limit
        now = time.time()
        client.rate_limiter.request_windows["gemini-2.0-flash"] = [now - 1] * 15

        with pytest.raises(LLMError, match="Rate limit .* exceeded"):
            client.generate_content("Test prompt")

    def test_generate_content_empty_response(self, mock_genai, gemini_config):
        """Test handling of empty response."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = ""
        mock_model.generate_content.return_value.prompt_feedback = "Filtered"
        mock_genai.GenerativeModel.return_value = mock_model

        client = GeminiClient(api_key="test_key", config=gemini_config)
        with pytest.raises(LLMError, match="Empty response from Gemini API"):
            client.generate_content("Test prompt")

    def test_generate_content_retries(self, mock_genai, gemini_config):
        """Test retry behavior with exponential backoff."""
        mock_model = MagicMock()
        # Fail twice, succeed on third try
        mock_model.generate_content.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            MagicMock(text="Success"),
        ]
        mock_genai.GenerativeModel.return_value = mock_model

        client = GeminiClient(api_key="test_key", config=gemini_config)
        response = client.generate_content("Test prompt", retries=2)

        assert response == "Success"
        assert mock_model.generate_content.call_count == 3

    def test_generate_content_circuit_breaker(self, mock_genai, gemini_config):
        """Test circuit breaker activation after repeated failures."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_genai.GenerativeModel.return_value = mock_model

        client = GeminiClient(api_key="test_key", config=gemini_config)

        # Trigger failures up to circuit breaker threshold
        for _ in range(3):
            with pytest.raises(LLMError):
                client.generate_content("Test prompt", retries=0)

        # Next attempt should trigger circuit breaker
        with pytest.raises(LLMError, match="Circuit breaker open"):
            client.generate_content("Test prompt")
