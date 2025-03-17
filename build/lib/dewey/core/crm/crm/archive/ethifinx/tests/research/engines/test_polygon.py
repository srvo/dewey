"""
Tests for Polygon API Engine
=======================
"""

import pytest
import os
import aiohttp
from unittest.mock import patch, MagicMock
from ethifinx.research.engines.polygon import PolygonEngine


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"POLYGON_API_KEY": "test_key"}):
        yield


@pytest.fixture
async def engine(mock_env):
    """Create a PolygonEngine instance for testing."""
    async with PolygonEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization(mock_env):
    """Test that the engine initializes correctly."""
    engine = PolygonEngine(max_retries=2)
    assert isinstance(engine, PolygonEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio
async def test_process_method(engine):
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "Polygon engine ready"


@pytest.mark.asyncio
async def test_get_ticker_details(engine):
    """Test ticker details retrieval."""
    mock_response = {
        "results": {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "market": "stocks",
            "locale": "us",
            "primary_exchange": "NASDAQ",
            "type": "CS",
            "active": True,
            "currency_name": "usd",
            "cik": "0000320193",
            "composite_figi": "BBG000B9XRY4",
            "share_class_figi": "BBG001S5N8V8",
            "last_updated_utc": "2024-01-10"
        }
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_ticker_details("AAPL")
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_ticker_news(engine):
    """Test ticker news retrieval."""
    mock_response = {
        "results": [
            {
                "id": "nJjgGIDzTKqUUJB_n3F1tg",
                "publisher": {
                    "name": "Reuters",
                    "homepage_url": "https://www.reuters.com"
                },
                "title": "Apple stock hits new high",
                "author": "John Doe",
                "published_utc": "2024-01-10T12:00:00Z",
                "article_url": "https://www.reuters.com/article/123",
                "tickers": ["AAPL"],
                "description": "Apple stock reaches new all-time high"
            }
        ],
        "status": "OK",
        "request_id": "123abc",
        "count": 1
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_ticker_news("AAPL", limit=1)
        
        assert result == mock_response
        mock_get.assert_called_once()
        
        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["ticker"] == "AAPL"
        assert params["limit"] == 1


@pytest.mark.asyncio
async def test_get_aggregates(engine):
    """Test aggregates retrieval."""
    mock_response = {
        "ticker": "AAPL",
        "status": "OK",
        "queryCount": 5,
        "resultsCount": 5,
        "adjusted": True,
        "results": [
            {
                "v": 80000000,  # volume
                "vw": 150.5,    # volume weighted price
                "o": 149.0,     # open
                "c": 151.0,     # close
                "h": 152.0,     # high
                "l": 148.0,     # low
                "t": 1641772800000,  # timestamp
                "n": 500000     # number of transactions
            }
        ]
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_aggregates(
            "AAPL",
            multiplier=1,
            timespan="day",
            from_date="2024-01-01",
            to_date="2024-01-10"
        )
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_daily_open_close(engine):
    """Test daily open/close retrieval."""
    mock_response = {
        "status": "OK",
        "from": "2024-01-10",
        "symbol": "AAPL",
        "open": 149.0,
        "high": 152.0,
        "low": 148.0,
        "close": 151.0,
        "volume": 80000000,
        "afterHours": 151.5,
        "preMarket": 148.5
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_daily_open_close("AAPL", "2024-01-10")
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_trades(engine):
    """Test trades retrieval."""
    mock_response = {
        "results": [
            {
                "conditions": [1],
                "exchange": 11,
                "id": "123",
                "participant_timestamp": 1641772800000,
                "price": 150.5,
                "sequence_number": 1,
                "size": 100,
                "tape": 1
            }
        ],
        "status": "OK",
        "request_id": "123abc",
        "next_url": "https://api.polygon.io/v3/trades/AAPL/2024-01-10?cursor=abc"
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_trades("AAPL", "2024-01-10", limit=1)
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_quotes(engine):
    """Test quotes retrieval."""
    mock_response = {
        "results": [
            {
                "ask_exchange": 11,
                "ask_price": 150.6,
                "ask_size": 100,
                "bid_exchange": 12,
                "bid_price": 150.4,
                "bid_size": 200,
                "conditions": [1],
                "indicators": [1],
                "participant_timestamp": 1641772800000,
                "sequence_number": 1,
                "tape": 1
            }
        ],
        "status": "OK",
        "request_id": "123abc",
        "next_url": "https://api.polygon.io/v3/quotes/AAPL/2024-01-10?cursor=abc"
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_quotes("AAPL", "2024-01-10", limit=1)
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_financials(engine):
    """Test financials retrieval."""
    mock_response = {
        "status": "OK",
        "count": 1,
        "results": [
            {
                "ticker": "AAPL",
                "period": "Y",
                "calendar_date": "2023-12-31",
                "report_period": "2023-12-31",
                "updated": "2024-01-10",
                "assets": 500000000000,
                "current_assets": 150000000000,
                "liabilities": 300000000000,
                "current_liabilities": 100000000000,
                "equity": 200000000000,
                "revenue": 100000000000,
                "net_income": 20000000000
            }
        ]
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_financials("AAPL", limit=1)
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_market_status(engine):
    """Test market status retrieval."""
    mock_response = {
        "market": "open",
        "serverTime": "2024-01-10T14:30:00.000Z",
        "exchanges": {
            "nyse": "open",
            "nasdaq": "open",
            "otc": "open"
        },
        "currencies": {
            "fx": "open",
            "crypto": "open"
        }
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_market_status()
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_search_retry_on_error(engine):
    """Test search retries on API errors."""
    mock_response = {"results": [{"ticker": "AAPL"}]}

    with patch("aiohttp.ClientSession.get") as mock_get:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()
        
        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response
        
        mock_get.side_effect = [mock_error_context, mock_success_context]

        result = await engine.get_ticker_details("AAPL")
        
        assert result == mock_response
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="Polygon API key not found"):
            PolygonEngine() 