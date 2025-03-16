"""Test tick processor service."""

from unittest.mock import AsyncMock

import pytest
from ecic.models.investment import AssetType, Investment
from ecic.services.tick_processor import TickProcessor


@pytest.mark.asyncio
async def test_process_tick() -> None:
    """Test processing a single price tick."""
    investment = Investment(
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=100,
        entry_price=150.0,
    )

    tick_data = {"price": 160.0, "volume": 1000000, "timestamp": "2024-01-01T12:00:00Z"}

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_price_service = AsyncMock()
    mock_price_service.get_price = AsyncMock(return_value=tick_data)

    processor = TickProcessor(session=mock_session, price_service=mock_price_service)
    await processor.process_tick(investment)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_tick_invalid_data() -> None:
    """Test processing invalid tick data."""
    investment = Investment(
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=100,
        entry_price=150.0,
    )

    invalid_data = {"price": "invalid", "volume": None, "timestamp": "invalid"}

    mock_session = AsyncMock()
    mock_price_service = AsyncMock()
    mock_price_service.get_price = AsyncMock(return_value=invalid_data)

    processor = TickProcessor(session=mock_session, price_service=mock_price_service)
    with pytest.raises(ValueError):
        await processor.process_tick(investment)


@pytest.mark.asyncio
async def test_process_tick_batch() -> None:
    """Test processing multiple ticks."""
    investments = [
        Investment(
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            quantity=100,
            entry_price=150.0,
        ),
        Investment(
            symbol="GOOGL",
            asset_type=AssetType.STOCK,
            quantity=50,
            entry_price=2500.0,
        ),
    ]

    tick_data = [
        {"price": 160.0, "volume": 1000000, "timestamp": "2024-01-01T12:00:00Z"},
        {"price": 2600.0, "volume": 500000, "timestamp": "2024-01-01T12:00:00Z"},
    ]

    mock_session = AsyncMock()
    mock_price_service = AsyncMock()
    mock_price_service.get_price = AsyncMock(side_effect=tick_data)

    processor = TickProcessor(session=mock_session, price_service=mock_price_service)
    await processor.process_tick_batch(investments)
