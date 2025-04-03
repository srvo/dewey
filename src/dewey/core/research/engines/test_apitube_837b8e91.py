# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Tests for APITube News Engine.
=========================
"""

import os
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from ethifinx.research.engines.apitube import APITubeEngine


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"APITUBE_API_KEY": "test_key"}):
        yield


@pytest.fixture
async def engine(mock_env):
    """Create an APITubeEngine instance for testing."""
    async with APITubeEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization(mock_env) -> None:
    """Test that the engine initializes correctly."""
    engine = APITubeEngine(max_retries=2)
    assert isinstance(engine, APITubeEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio
async def test_process_method(engine) -> None:
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "APITube engine ready"


@pytest.mark.asyncio
async def test_search_news_basic(engine) -> None:
    """Test basic news search functionality."""
    mock_response = {
        "articles": [
            {
                "title": "Test Article",
                "url": "https://example.com/news",
                "description": "Test description",
                "source": {"name": "Test Source", "domain": "example.com"},
                "published_at": "2024-01-01T12:00:00Z",
            },
        ],
        "total_results": 1,
        "page": 1,
        "page_size": 20,
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.search_news("test query")

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify API parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["q"] == "test query"
        assert params["page"] == 1
        assert params["page_size"] == 20


@pytest.mark.asyncio
async def test_search_news_with_filters(engine) -> None:
    """Test news search with various filters."""
    mock_response = {"articles": []}

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.search_news(
            "test query",
            language="en",
            country="US",
            category="business",
            industry="technology",
            from_date="2024-01-01",
            to_date="2024-01-31",
            sort_by="date",
        )

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify filters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["q"] == "test query"
        assert params["language"] == "en"
        assert params["country"] == "US"
        assert params["category"] == "business"
        assert params["industry"] == "technology"
        assert params["from_date"] == "2024-01-01"
        assert params["to_date"] == "2024-01-31"
        assert params["sort_by"] == "date"


@pytest.mark.asyncio
async def test_trending_topics(engine) -> None:
    """Test trending topics functionality."""
    mock_response = {
        "topics": [{"topic": "Test Topic", "count": 100, "sentiment_score": 0.8}],
        "timeframe": "24h",
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.trending_topics(
            language="en",
            country="US",
            timeframe="24h",
        )

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["language"] == "en"
        assert params["country"] == "US"
        assert params["timeframe"] == "24h"


@pytest.mark.asyncio
async def test_sentiment_analysis(engine) -> None:
    """Test sentiment analysis functionality."""
    mock_response = {
        "sentiment": {
            "overall_score": 0.6,
            "positive": 75,
            "neutral": 20,
            "negative": 5,
            "timeline": [],
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.sentiment_analysis(
            "test query",
            from_date="2024-01-01",
            to_date="2024-01-31",
            language="en",
        )

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["q"] == "test query"
        assert params["from_date"] == "2024-01-01"
        assert params["to_date"] == "2024-01-31"
        assert params["language"] == "en"


@pytest.mark.asyncio
async def test_search_retry_on_error(engine) -> None:
    """Test search retries on API errors."""
    mock_response = {"articles": []}

    with patch("aiohttp.ClientSession.get") as mock_get:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()

        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response

        mock_get.side_effect = [mock_error_context, mock_success_context]

        result = await engine.search_news("test query")

        assert result == mock_response
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_missing_api_key() -> None:
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="APITube API key not found"):
            APITubeEngine()
