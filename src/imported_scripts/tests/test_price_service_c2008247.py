"""Tests for price service."""

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession
from ecic.models.investment import AssetType
from ecic.services.price_service import PriceService


@pytest.mark.asyncio
async def test_get_session() -> None:
    """Test session creation."""
    service = PriceService(api_key="test_key")
    session = await service.get_session()
    assert isinstance(session, ClientSession)
    await service.close()


@pytest.mark.asyncio
async def test_get_price() -> None:
    """Test price fetching."""
    mock_data = {"price": 150.0, "volume": 1000000, "timestamp": "2023-12-25T12:00:00Z"}

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_data)

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.close = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        service = PriceService(api_key="test_key")
        price_data = await service.get_price("AAPL", AssetType.STOCK)

        assert price_data is not None
        assert price_data["price"] == 150.0
        assert price_data["volume"] == 1000000
        await service.close()


@pytest.mark.asyncio
async def test_get_price_error() -> None:
    """Test price fetching with error."""
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.close = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        service = PriceService()
        price_data = await service.get_price("INVALID", AssetType.STOCK)

        assert price_data is None
        await service.close()


def test_endpoint_generation() -> None:
    """Test API endpoint generation."""
    service = PriceService()
    endpoint = service.get_endpoint("AAPL", AssetType.STOCK)
    assert isinstance(endpoint, str)
    assert "AAPL" in endpoint
