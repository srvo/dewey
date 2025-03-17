# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""Tests for Exa AI Research Engine.
============================
"""

import os
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from ethifinx.research.engines.exa import ExaEngine


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"EXA_API_KEY": "test_key"}):
        yield


@pytest.fixture
async def engine(mock_env):
    """Create an ExaEngine instance for testing."""
    async with ExaEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization(mock_env) -> None:
    """Test that the engine initializes correctly."""
    engine = ExaEngine(max_retries=2)
    assert isinstance(engine, ExaEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio
async def test_process_method(engine) -> None:
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "Exa engine ready"


@pytest.mark.asyncio
async def test_search_basic(engine) -> None:
    """Test basic search functionality."""
    mock_response = {
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "text": "Test content",
                "highlights": ["Relevant snippet"],
            },
        ],
        "autoprompt": "enhanced query",
    }

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value = mock_context

        result = await engine.search("test query")

        assert result == mock_response
        mock_post.assert_called_once()

        # Verify API parameters
        call_args = mock_post.call_args
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert payload["query"] == "test query"
        assert payload["num_results"] == 10
        assert payload["use_autoprompt"] is True
        assert payload["highlights"] is True
        assert payload["text"] is True


@pytest.mark.asyncio
async def test_search_with_filters(engine) -> None:
    """Test search with domain and date filters."""
    mock_response = {"results": []}

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value = mock_context

        result = await engine.search(
            "test query",
            include_domains=["example.com"],
            exclude_domains=["spam.com"],
            start_published_date="2023-01-01",
            end_published_date="2024-01-01",
        )

        assert result == mock_response
        mock_post.assert_called_once()

        # Verify filters
        call_args = mock_post.call_args
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert payload["include_domains"] == ["example.com"]
        assert payload["exclude_domains"] == ["spam.com"]
        assert payload["start_published_date"] == "2023-01-01"
        assert payload["end_published_date"] == "2024-01-01"


@pytest.mark.asyncio
async def test_get_contents(engine) -> None:
    """Test content retrieval functionality."""
    mock_response = {
        "results": [
            {
                "url": "https://example.com",
                "text": "Parsed content",
                "html": "<article>Cleaned HTML</article>",
            },
        ],
    }

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value = mock_context

        result = await engine.get_contents(
            ["https://example.com"],
            text=True,
            html=True,
        )

        assert result == mock_response
        mock_post.assert_called_once()

        # Verify parameters
        call_args = mock_post.call_args
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert payload["urls"] == ["https://example.com"]
        assert payload["text"] is True
        assert payload["html"] is True


@pytest.mark.asyncio
async def test_find_similar(engine) -> None:
    """Test similar pages functionality."""
    mock_response = {
        "results": [
            {
                "title": "Similar Result",
                "url": "https://similar.com",
                "text": "Related content",
                "highlights": ["Similar context"],
            },
        ],
    }

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value = mock_context

        result = await engine.find_similar(
            "https://example.com",
            include_domains=["trusted.com"],
        )

        assert result == mock_response
        mock_post.assert_called_once()

        # Verify parameters
        call_args = mock_post.call_args
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert payload["url"] == "https://example.com"
        assert payload["include_domains"] == ["trusted.com"]


@pytest.mark.asyncio
async def test_search_retry_on_error(engine) -> None:
    """Test search retries on API errors."""
    mock_response = {"results": []}

    with patch("aiohttp.ClientSession.post") as mock_post:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()

        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response

        mock_post.side_effect = [mock_error_context, mock_success_context]

        result = await engine.search("test query")

        assert result == mock_response
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_missing_api_key() -> None:
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="Exa API key not found"):
            ExaEngine()
