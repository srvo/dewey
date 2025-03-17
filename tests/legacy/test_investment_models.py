
# Refactored from: test_investment_models
# Date: 2025-03-16T16:19:08.845642
# Refactor Version: 1.0
"""Tests for investment models."""

from datetime import datetime

from ecic.models.investment import AssetType, ESGRating, Investment, PriceTick


def test_investment_creation() -> None:
    """Test creating an investment."""
    investment = Investment(
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=100,
        entry_price=150.0,
        current_price=160.0,
        esg_rating=ESGRating.A,
    )

    assert investment.symbol == "AAPL"
    assert investment.asset_type == AssetType.STOCK
    assert investment.quantity == 100
    assert investment.entry_price == 150.0
    assert investment.current_price == 160.0
    assert investment.esg_rating == ESGRating.A


def test_investment_market_value() -> None:
    """Test market value calculation."""
    investment = Investment(
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=100,
        entry_price=150.0,
        current_price=160.0,
    )

    assert investment.market_value == 16000.0


def test_investment_profit_loss() -> None:
    """Test profit/loss calculation."""
    investment = Investment(
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=100,
        entry_price=150.0,
        current_price=160.0,
    )

    assert investment.profit_loss == 1000.0


def test_price_tick_creation() -> None:
    """Test creating a price tick."""
    investment = Investment(
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=100,
        entry_price=150.0,
    )

    tick = PriceTick(
        investment=investment,
        price=160.0,
        volume=1000000,
        timestamp=datetime.utcnow(),
    )

    assert tick.price == 160.0
    assert tick.volume == 1000000
    assert tick.investment == investment
