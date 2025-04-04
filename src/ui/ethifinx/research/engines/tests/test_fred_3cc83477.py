# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

"""
Tests for FRED API Engine.
====================
"""

import os
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from ethifinx.research.engines.fred import FREDEngine


@pytest.fixture()
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"FRED_API_KEY": "test_key"}):
        yield


@pytest.fixture()
async def engine(mock_env):
    """Create a FREDEngine instance for testing."""
    engine = FREDEngine(max_retries=2)
    await engine._ensure_session()
    try:
        return engine
    finally:
        await engine._close_session()


@pytest.mark.asyncio()
async def test_engine_initialization(mock_env) -> None:
    """Test that the engine initializes correctly."""
    engine = FREDEngine(max_retries=2)
    assert isinstance(engine, FREDEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio()
async def test_process_method(engine) -> None:
    """Test the process method returns expected status."""
    engine = await engine
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "FRED engine ready"


@pytest.mark.asyncio()
async def test_get_category(engine) -> None:
    """Test category retrieval."""
    engine = await engine
    mock_response = {
        "categories": [
            {
                "id": 125,
                "name": "Trade Balance",
                "parent_id": 13,
                "notes": "International Trade Balance",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_category(125)

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["category_id"] == 125
        assert params["api_key"] == "test_key"
        assert params["file_type"] == "json"


@pytest.mark.asyncio()
async def test_get_category_children(engine) -> None:
    """Test category children retrieval."""
    engine = await engine
    mock_response = {
        "categories": [
            {"id": 126, "name": "Exports", "parent_id": 125},
            {"id": 127, "name": "Imports", "parent_id": 125},
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_category_children(125)

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio()
async def test_get_category_series(engine) -> None:
    """Test category series retrieval."""
    engine = await engine
    mock_response = {
        "seriess": [
            {
                "id": "BOPGSTB",
                "title": "Trade Balance: Goods and Services",
                "observation_start": "1960-01-01",
                "observation_end": "2024-01-01",
                "frequency": "Monthly",
                "units": "Billions of Dollars",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_category_series(125, limit=1)

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio()
async def test_get_series(engine) -> None:
    """Test series retrieval."""
    engine = await engine
    mock_response = {
        "seriess": [
            {
                "id": "GDP",
                "title": "Gross Domestic Product",
                "observation_start": "1947-01-01",
                "observation_end": "2024-01-01",
                "frequency": "Quarterly",
                "units": "Billions of Dollars",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_series("GDP")

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio()
async def test_get_series_observations(engine) -> None:
    """Test series observations retrieval."""
    engine = await engine
    mock_response = {
        "observations": [
            {
                "date": "2024-01-01",
                "value": "24000.5",
                "realtime_start": "2024-01-01",
                "realtime_end": "2024-01-01",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_series_observations(
            "GDP", observation_start="2024-01-01", observation_end="2024-01-01",
        )

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio()
async def test_search_series(engine) -> None:
    """Test series search."""
    engine = await engine
    mock_response = {
        "seriess": [
            {
                "id": "GDP",
                "title": "Gross Domestic Product",
                "observation_start": "1947-01-01",
                "observation_end": "2024-01-01",
                "frequency": "Quarterly",
                "units": "Billions of Dollars",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.search_series("GDP", limit=1)

        assert result == mock_response
        mock_get.assert_called_once()

        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["search_text"] == "GDP"
        assert params["limit"] == 1


@pytest.mark.asyncio()
async def test_get_releases(engine) -> None:
    """Test releases retrieval."""
    engine = await engine
    mock_response = {
        "releases": [
            {
                "id": 53,
                "name": "Gross Domestic Product",
                "press_release": True,
                "link": "http://www.bea.gov/newsreleases/national/gdp/gdpnewsrelease.htm",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_releases(limit=1)

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio()
async def test_get_release_dates(engine) -> None:
    """Test release dates retrieval."""
    engine = await engine
    mock_response = {
        "release_dates": [
            {
                "release_id": 53,
                "release_name": "Gross Domestic Product",
                "date": "2024-01-25",
            },
        ],
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }
        mock_get.return_value = mock_context

        result = await engine.get_release_dates(limit=1)

        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio()
async def test_search_retry_on_error(engine) -> None:
    """Test search retries on API errors."""
    engine = await engine
    mock_response = {"seriess": [{"id": "GDP"}]}

    with patch("aiohttp.ClientSession.get") as mock_get:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()

        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response
        mock_success_context.__aenter__.return_value.headers = {
            "Content-Type": "application/json",
        }

        mock_get.side_effect = [mock_error_context, mock_success_context]

        result = await engine.search_series("GDP")

        assert result == mock_response
        assert mock_get.call_count == 2


@pytest.mark.asyncio()
async def test_missing_api_key() -> None:
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="FRED API key not found"):
            FREDEngine()
