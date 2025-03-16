# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Tests for Brave Search Engine.
=========================
"""

import os
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from ethifinx.research.engines.brave import BraveSearchEngine


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"BRAVE_API_KEY": "test_key"}):
        yield


@pytest.fixture
async def engine(mock_env):
    """Create a BraveSearchEngine instance for testing."""
    async with BraveSearchEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization(mock_env) -> None:
    """Test that the engine initializes correctly."""
    engine = BraveSearchEngine(max_retries=2)
    assert isinstance(engine, BraveSearchEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio
async def test_process_method(engine) -> None:
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "Brave Search engine ready"


@pytest.mark.asyncio
async def test_web_search_basic(engine) -> None:
    """Test basic web search functionality."""
    mock_response = {
        "query": {"original": "test query"},
        "web": {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "description": "Test description",
                },
            ],
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.web_search("test query")

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify API parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["q"] == "test query"


@pytest.mark.asyncio
async def test_web_search_with_options(engine) -> None:
    """Test web search with additional options."""
    mock_response = {"web": {"results": []}}

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.web_search(
            "test query",
            count=10,
            offset=20,
            country="US",
            search_lang="en",
            safesearch="strict",
        )

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify all parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["q"] == "test query"
        assert params["count"] == 10
        assert params["offset"] == 20
        assert params["country"] == "US"
        assert params["search_lang"] == "en"
        assert params["safesearch"] == "strict"


@pytest.mark.asyncio
async def test_local_search_basic(engine) -> None:
    """Test basic local search functionality."""
    mock_search_response = {"web": {"results": []}}

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_search_response
        mock_get.return_value = mock_context

        result = await engine.local_search("restaurants in San Francisco")

        assert result == mock_search_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_local_search_with_details(engine) -> None:
    """Test local search with location details."""
    mock_responses = {
        "web/search": {"web": {"results": []}},
        "local/pois": {"locations": []},
        "local/descriptions": {"descriptions": []},
    }

    with patch("aiohttp.ClientSession.get") as mock_get:

        def get_mock_response(url, **kwargs):
            endpoint = url.split("/")[-2] + "/" + url.split("/")[-1]
            mock_context = MagicMock()
            mock_context.__aenter__.return_value.status = 200
            mock_context.__aenter__.return_value.json.return_value = mock_responses[
                endpoint
            ]
            return mock_context

        mock_get.side_effect = get_mock_response

        result = await engine.local_search(
            "restaurants in San Francisco",
            location_ids=["loc1", "loc2"],
        )

        assert "search_results" in result
        assert "location_details" in result
        assert "descriptions" in result
        assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_search_retry_on_error(engine) -> None:
    """Test search retries on API errors."""
    mock_response = {"web": {"results": []}}

    with patch("aiohttp.ClientSession.get") as mock_get:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()

        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response

        mock_get.side_effect = [mock_error_context, mock_success_context]

        result = await engine.web_search("test query")

        assert result == mock_response
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_missing_api_key() -> None:
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="Brave Search API key not found"):
            BraveSearchEngine()
