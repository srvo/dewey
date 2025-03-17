"""
Tests for Tavily Research Engine
=============================
"""

import pytest
import os
import aiohttp
from unittest.mock import patch, MagicMock
from ethifinx.research.engines.tavily import TavilyEngine


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"TAVILY_API_KEY": "test_key"}):
        yield


@pytest.fixture
async def engine(mock_env):
    """Create a TavilyEngine instance for testing."""
    async with TavilyEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization(mock_env):
    """Test that the engine initializes correctly."""
    engine = TavilyEngine(max_retries=2)
    assert isinstance(engine, TavilyEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio
async def test_process_method(engine):
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "Tavily engine ready"


@pytest.mark.asyncio
async def test_search_basic(engine):
    """Test basic search functionality."""
    mock_response = {
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content"
            }
        ],
        "query": "test query"
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
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        payload = call_kwargs["json"]
        assert payload["query"] == "test query"
        assert payload["search_depth"] == "basic"
        assert payload["topic"] == "general"
        assert payload["max_results"] == 5


@pytest.mark.asyncio
async def test_search_news(engine):
    """Test news-specific search functionality."""
    mock_response = {
        "results": [
            {
                "title": "News Result",
                "url": "https://news.com",
                "content": "News content"
            }
        ],
        "query": "news query"
    }

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value = mock_context

        result = await engine.search_news("news query", days=7)
        
        assert result == mock_response
        mock_post.assert_called_once()
        
        # Verify news-specific parameters
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        payload = call_kwargs["json"]
        assert payload["query"] == "news query"
        assert payload["topic"] == "news"
        assert payload["days"] == 7


@pytest.mark.asyncio
async def test_search_with_domains(engine):
    """Test search with domain filtering."""
    mock_response = {"results": []}

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value = mock_context

        result = await engine.search(
            "test query",
            include_domains=["example.com"],
            exclude_domains=["spam.com"]
        )
        
        assert result == mock_response
        mock_post.assert_called_once()
        
        # Verify domain filtering parameters
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        payload = call_kwargs["json"]
        assert payload["include_domains"] == ["example.com"]
        assert payload["exclude_domains"] == ["spam.com"]


@pytest.mark.asyncio
async def test_search_retry_on_error(engine):
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
async def test_missing_api_key():
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="Tavily API key not found"):
            TavilyEngine() 