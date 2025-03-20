"""Tests for financial analysis workflow."""

import pytest
from unittest.mock import patch
from datetime import datetime
import pandas as pd
from dewey.core.research.analysis.financial_analysis import (
    get_current_universe,
    analyze_financial_changes,
    analyze_material_events,
    main as financial_main,
)


class TestFinancialAnalysis:
    """Test suite for financial analysis functions."""

    @pytest.fixture
    def mock_stocks_data(self):
        """Create mock stocks data."""
        return pd.DataFrame(
            {
                "ticker": ["TEST", "ANTR"],
                "name": ["Test Corp", "Another Corp"],
                "sector": ["Tech", "Finance"],
                "industry": ["Software", "Banking"],
            }
        )

    @pytest.fixture
    def mock_metrics_data(self):
        """Create mock financial metrics data."""
        return pd.DataFrame(
            {
                "metric_name": ["Assets", "Revenues"],
                "current_value": [1000000, 500000],
                "prev_value": [800000, 400000],
                "end_date": [datetime.now(), datetime.now()],
                "filed_date": [datetime.now(), datetime.now()],
                "pct_change": [25.0, 25.0],
            }
        )

    def test_get_current_universe(self, mock_db_connection, mock_stocks_data):
        """Test getting current universe of stocks."""
        mock_db_connection.execute.return_value.fetchdf.return_value = mock_stocks_data

        with patch(
            "dewey.core.research.analysis.financial_analysis.get_connection",
            return_value=mock_db_connection,
        ):
            stocks = get_current_universe()

            assert len(stocks) == 2
            assert stocks[0]["ticker"] == "TEST"
            assert stocks[1]["ticker"] == "ANTR"
            mock_db_connection.execute.assert_called_once()

    def test_analyze_financial_changes(self, mock_db_connection, mock_metrics_data):
        """Test analyzing financial metric changes."""
        mock_db_connection.execute.return_value.fetchdf.return_value = mock_metrics_data

        with patch(
            "dewey.core.research.analysis.financial_analysis.get_connection",
            return_value=mock_db_connection,
        ):
            changes = analyze_financial_changes("TEST")

            assert len(changes) == 2
            assert changes[0]["metric_name"] == "Assets"
            assert changes[0]["pct_change"] == 25.0
            mock_db_connection.execute.assert_called_once()

    def test_analyze_material_events(self, mock_db_connection, mock_metrics_data):
        """Test analyzing material events."""
        mock_db_connection.execute.return_value.fetchdf.return_value = mock_metrics_data

        with patch(
            "dewey.core.research.analysis.financial_analysis.get_connection",
            return_value=mock_db_connection,
        ):
            with patch(
                "dewey.core.research.analysis.financial_analysis.analyze_financial_changes",
                return_value=mock_metrics_data.to_dict("records"),
            ):
                events = analyze_material_events("TEST")

                assert len(events) > 0
                assert any("MAJOR CHANGE" in event for event in events)
                mock_db_connection.execute.assert_called()

    def test_main_function(
        self, mock_db_connection, mock_stocks_data, mock_metrics_data
    ):
        """Test main analysis function."""
        mock_db_connection.execute.return_value.fetchdf.side_effect = [
            mock_stocks_data,  # for get_current_universe
            mock_metrics_data,  # for analyze_material_events
        ]

        with patch(
            "dewey.core.research.analysis.financial_analysis.get_connection",
            return_value=mock_db_connection,
        ):
            with patch(
                "dewey.core.research.analysis.financial_analysis.analyze_material_events",
                return_value=["Test event"],
            ):
                financial_main()
                assert mock_db_connection.execute.call_count >= 2

    def test_main_function_error_handling(self, mock_db_connection):
        """Test error handling in main function."""
        mock_db_connection.execute.side_effect = Exception("Database error")

        with patch(
            "dewey.core.research.analysis.financial_analysis.get_connection",
            return_value=mock_db_connection,
        ):
            with pytest.raises(Exception):
                financial_main()

    @pytest.mark.integration
    def test_full_analysis_workflow(
        self, mock_db_connection, mock_stocks_data, mock_metrics_data
    ):
        """Integration test for full financial analysis workflow."""
        mock_db_connection.execute.return_value.fetchdf.side_effect = [
            mock_stocks_data,  # for get_current_universe
            mock_metrics_data,  # for analyze_financial_changes
            mock_metrics_data,  # for analyze_material_events
        ]

        with patch(
            "dewey.core.research.analysis.financial_analysis.get_connection",
            return_value=mock_db_connection,
        ):
            # Get universe
            stocks = get_current_universe()
            assert len(stocks) > 0

            # Analyze each stock
            for stock in stocks:
                # Check financial changes
                changes = analyze_financial_changes(stock["ticker"])
                assert len(changes) > 0

                # Check material events
                events = analyze_material_events(stock["ticker"])
                assert len(events) > 0

            assert mock_db_connection.execute.call_count >= 3
