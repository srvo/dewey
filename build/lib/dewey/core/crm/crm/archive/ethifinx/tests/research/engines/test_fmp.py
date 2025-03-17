"""
Tests for Financial Modeling Prep Engine
===================================
"""

import pytest
import os
import aiohttp
from unittest.mock import patch, MagicMock
from ethifinx.research.engines.fmp import FMPEngine


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
        yield


@pytest.fixture
async def engine(mock_env):
    """Create a FMPEngine instance for testing."""
    async with FMPEngine(max_retries=2) as engine:
        yield engine


@pytest.mark.asyncio
async def test_engine_initialization(mock_env):
    """Test that the engine initializes correctly."""
    engine = FMPEngine(max_retries=2)
    assert isinstance(engine, FMPEngine)
    assert engine.max_retries == 2
    assert engine.api_key == "test_key"


@pytest.mark.asyncio
async def test_process_method(engine):
    """Test the process method returns expected status."""
    result = await engine.process()
    assert isinstance(result, dict)
    assert result["status"] == "FMP engine ready"


@pytest.mark.asyncio
async def test_search_company(engine):
    """Test company search functionality."""
    mock_response = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "currency": "USD",
            "stockExchange": "NASDAQ",
            "exchangeShortName": "NASDAQ"
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.search_company("Apple", limit=1)
        
        assert result == mock_response
        mock_get.assert_called_once()
        
        # Verify API parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["query"] == "Apple"
        assert params["limit"] == 1
        assert params["apikey"] == "test_key"


@pytest.mark.asyncio
async def test_get_company_profile(engine):
    """Test company profile retrieval."""
    mock_response = [
        {
            "symbol": "AAPL",
            "price": 150.0,
            "beta": 1.2,
            "volAvg": 80000000,
            "mktCap": 2500000000000,
            "companyName": "Apple Inc.",
            "industry": "Consumer Electronics"
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_company_profile("AAPL")
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_quote(engine):
    """Test stock quote retrieval."""
    mock_response = [
        {
            "symbol": "AAPL",
            "price": 150.0,
            "volume": 80000000,
            "change": 2.5,
            "changesPercentage": 1.67
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_quote("AAPL")
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_financial_statements(engine):
    """Test financial statements retrieval."""
    mock_response = [
        {
            "date": "2023-12-31",
            "symbol": "AAPL",
            "reportedCurrency": "USD",
            "revenue": 100000000000,
            "netIncome": 20000000000
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_financial_statements(
            "AAPL",
            statement="income",
            period="annual",
            limit=1
        )
        
        assert result == mock_response
        mock_get.assert_called_once()
        
        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["period"] == "annual"
        assert params["limit"] == 1


@pytest.mark.asyncio
async def test_get_key_metrics(engine):
    """Test key metrics retrieval."""
    mock_response = [
        {
            "date": "2023-12-31",
            "symbol": "AAPL",
            "peRatio": 25.5,
            "pbRatio": 15.2,
            "debtToEquity": 1.5
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_key_metrics("AAPL")
        
        assert result == mock_response
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_historical_price(engine):
    """Test historical price data retrieval."""
    mock_response = {
        "symbol": "AAPL",
        "historical": [
            {
                "date": "2024-01-10",
                "open": 150.0,
                "high": 152.0,
                "low": 149.0,
                "close": 151.0,
                "volume": 80000000
            }
        ]
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value.status = 200
        mock_context.__aenter__.return_value.json.return_value = mock_response
        mock_get.return_value = mock_context

        result = await engine.get_historical_price(
            "AAPL",
            from_date="2024-01-01",
            to_date="2024-01-10"
        )
        
        assert result == mock_response
        mock_get.assert_called_once()
        
        # Verify parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["from"] == "2024-01-01"
        assert params["to"] == "2024-01-10"


@pytest.mark.asyncio
async def test_search_retry_on_error(engine):
    """Test search retries on API errors."""
    mock_response = [{"symbol": "AAPL"}]

    with patch("aiohttp.ClientSession.get") as mock_get:
        # First call raises error, second succeeds
        mock_error_context = MagicMock()
        mock_error_context.__aenter__.side_effect = aiohttp.ClientError()
        
        mock_success_context = MagicMock()
        mock_success_context.__aenter__.return_value.status = 200
        mock_success_context.__aenter__.return_value.json.return_value = mock_response
        
        mock_get.side_effect = [mock_error_context, mock_success_context]

        result = await engine.search_company("AAPL")
        
        assert result == mock_response
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test error handling for missing API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="FMP API key not found"):
            FMPEngine() 