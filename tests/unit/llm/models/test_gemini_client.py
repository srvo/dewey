import pytest
import logging
import time
from datetime import datetime
from unittest.mock import patch

from dewey.llm.exceptions import LLMError
from dewey.llm.api_clients.gemini import GeminiClient, RateLimiter
from pathlib import Path
import os
import json

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset RateLimiter state between tests to prevent interference"""
    limiter = RateLimiter()
    limiter.request_windows = {}
    limiter.daily_requests = {}
    limiter.daily_start_time = {}
    limiter.last_request_time = {}
    limiter.failure_counts = {}
    limiter.circuit_open_until = {}
    yield


def test_rate_limiter_rpm_limit():
    """Verify RPM limit enforcement for gemini-2.0-flash model"""
    model = "gemini-2.0-flash"
    limiter = RateLimiter()
    rpm = limiter.MODEL_LIMITS[model]["rpm"]

    # Make RPM+1 requests in a minute
    for _ in range(rpm):
        limiter.check_limit(model, "test prompt")

    # Last request should fail
    with pytest.raises(
        LLMError, match=f"Rate limit \\({rpm} requests/minute\\) exceeded"
    ):
        limiter.check_limit(model, "test prompt")


def test_rate_limiter_circuit_breaker():
    """Test circuit breaker activation after consecutive failures"""
    model = "gemini-2.0-flash"
    limiter = RateLimiter()
    threshold = limiter.MODEL_LIMITS[model]["circuit_breaker_threshold"]

    now = time.time()
    for _ in range(threshold + 1):
        limiter._record_failure(model, now)

    assert model in limiter.circuit_open_until
    assert limiter.circuit_open_until[model] > now


def test_rate_limiter_daily_limit():
    """Validate daily request limit enforcement"""
    model = "gemini-2.0-flash"
    limiter = RateLimiter()
    rpd = limiter.MODEL_LIMITS[model]["rpd"]

    # Simulate end of day
    limiter.daily_start_time[model] = time.time() - 86400

    # Make RPD+1 requests
    for _ in range(rpd):
        limiter.check_limit(model, "test")

    with pytest.raises(LLMError, match=f"Daily request limit \\({rpd}\\) reached"):
        limiter.check_limit(model, "test")


def test_rate_limiter_min_interval():
    """Verify minimum request interval enforcement"""
    model = "gemini-2.0-pro-experimental-02-05"
    limiter = RateLimiter()
    min_interval = limiter.MODEL_LIMITS[model]["min_request_interval"]

    initial_time = time.time()
    limiter.check_limit(model, "test")

    with patch("time.time", return_value=initial_time + min_interval - 1):
        with pytest.raises(LLMError, match=f"Rate limit"):
            limiter.check_limit(model, "test")


def test_gemini_client_init():
    """Test client initialization with valid API key"""
    client = GeminiClient()
    assert client.default_model == "gemini-2.0-flash-lite"
    assert isinstance(client.rate_limiter, RateLimiter)


def test_gemini_client_fallback_model():
    """Verify fallback model selection on rate limit"""
    client = GeminiClient()
    with patch("rich.prompt.Confirm.ask", return_value=True):
        result = client._use_deepinfra_fallback("test prompt")
        assert isinstance(result, str)


def test_save_llm_output():
    """Validate LLM output saving mechanism"""
    client = GeminiClient()
    prompt = "Test prompt"
    response = "Test response"
    model = "test_model"

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 1, 1)
        client._save_llm_output(prompt, response, model)

    output_dir = (
        Path(client.config.get("project_root", os.getcwd())) / "docs" / "llm_outputs"
    )
    expected_file = output_dir / "llm_output_20230101_000000_000000.json"

    with open(expected_file, "r") as f:
        data = json.load(f)
        assert data["prompt"] == prompt
        assert data["response"] == response
        assert data["model"] == model


def test_generate_content_retry():
    """Test retry logic with mocked failures"""
    client = GeminiClient()

    with patch.object(GeminiClient, "_get_model") as mock_get_model:
        mock_get_model.side_effect = Exception("Simulated error")
        with pytest.raises(LLMError, match="Failed after 3 attempts"):
            client.generate_content("test", retries=3)


def test_context_caching():
    """Validate context caching functionality"""
    client = GeminiClient()
    cache_key = "test_cache"

    client.clear_context_cache(cache_key)
    assert cache_key not in client.context_cache

    client.generate_content("test", cache_context=True, cache_key=cache_key)
    assert client.context_cache[cache_key] == "test"


def test_media_input_handling():
    """Verify media input processing"""
    client = GeminiClient()
    media = [{"type": "image", "data": "base64string"}]

    with patch("google.generativeai.GenerativeModel.generate_content") as mock_gen:
        client.generate_content("test", media_inputs=media)
        mock_gen.assert_called_with(contents=[{"media": media[0]}, {"text": "test"}])
