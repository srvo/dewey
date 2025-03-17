
# Refactored from: test_portfolio_widget
# Date: 2025-03-16T16:19:09.688845
# Refactor Version: 1.0
"""Test portfolio widget."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from ecic.models.investment import AssetType, ESGRating, Investment
from ecic.widgets.portfolio import PortfolioWidget
from textual.widgets import DataTable

from .widget_test_base import WidgetTestBase


class TestPortfolioWidget(WidgetTestBase[PortfolioWidget]):
    """Test cases for portfolio widget."""

    @pytest.fixture
    def widget_class(self):
        """Get widget class for testing."""
        return PortfolioWidget

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.query = MagicMock()
        return session

    @pytest.fixture
    def sample_investments(self):
        """Create sample investment data."""
        return [
            Investment(
                symbol="AAPL",
                asset_type=AssetType.STOCK,
                quantity=100,
                entry_price=150.0,
                current_price=160.0,
                esg_rating=ESGRating.A,
            ),
            Investment(
                symbol="GOOGL",
                asset_type=AssetType.STOCK,
                quantity=50,
                entry_price=2500.0,
                current_price=2600.0,
                esg_rating=ESGRating.B,
            ),
        ]

    @pytest.mark.asyncio
    async def test_portfolio_creation(self, app, widget) -> None:
        """Test portfolio widget creation."""
        assert isinstance(widget, PortfolioWidget)
        table = widget.query_one(DataTable)
        assert table is not None

        # Check column headers
        assert "Symbol" in table.columns
        assert "Type" in table.columns
        assert "Quantity" in table.columns
        assert "Entry Price" in table.columns
        assert "Current Price" in table.columns
        assert "Market Value" in table.columns
        assert "P/L" in table.columns
        assert "ESG" in table.columns

    @pytest.mark.asyncio
    async def test_portfolio_data_loading(
        self,
        app,
        widget,
        mock_session,
        sample_investments,
    ) -> None:
        """Test loading portfolio data."""
        mock_session.query.return_value.all = AsyncMock(return_value=sample_investments)
        widget.session = mock_session

        await widget.load_data()
        table = widget.query_one(DataTable)

        assert len(table.rows) == 2

        # Check first row
        row = table.get_row(0)
        assert row[0] == "AAPL"  # Symbol
        assert row[1] == "stock"  # Type
        assert float(row[2]) == 100  # Quantity
        assert float(row[3]) == 150.0  # Entry Price
        assert float(row[4]) == 160.0  # Current Price
        assert float(row[5]) == 16000.0  # Market Value
        assert float(row[6]) == 1000.0  # P/L
        assert row[7] == "A"  # ESG Rating

    @pytest.mark.asyncio
    async def test_portfolio_sorting(
        self,
        app,
        widget,
        mock_session,
        sample_investments,
    ) -> None:
        """Test portfolio sorting."""
        mock_session.query.return_value.all = AsyncMock(return_value=sample_investments)
        widget.session = mock_session

        await widget.load_data()
        table = widget.query_one(DataTable)

        # Sort by market value
        await widget.action_sort("Market Value")
        rows = list(table.rows)
        assert rows[0][0] == "GOOGL"  # Higher market value
        assert rows[1][0] == "AAPL"

        # Sort by ESG rating
        await widget.action_sort("ESG")
        rows = list(table.rows)
        assert rows[0][0] == "AAPL"  # Better ESG rating
        assert rows[1][0] == "GOOGL"

    @pytest.mark.asyncio
    async def test_portfolio_filtering(
        self,
        app,
        widget,
        mock_session,
        sample_investments,
    ) -> None:
        """Test portfolio filtering."""
        mock_session.query.return_value.all = AsyncMock(return_value=sample_investments)
        widget.session = mock_session

        await widget.load_data()

        # Filter by symbol
        await widget.action_filter("AAPL")
        table = widget.query_one(DataTable)
        assert len(table.rows) == 1
        assert table.get_row(0)[0] == "AAPL"

        # Clear filter
        await widget.action_clear_filter()
        assert len(table.rows) == 2
