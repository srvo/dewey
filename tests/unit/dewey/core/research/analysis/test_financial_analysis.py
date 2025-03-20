import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dewey.core.db.connection import DatabaseConnection
from dewey.core.research.analysis.financial_analysis import FinancialAnalysis


@pytest.fixture
def financial_analysis() -> FinancialAnalysis:
    """Fixture for creating a FinancialAnalysis instance."""
    return FinancialAnalysis()


@pytest.fixture
def mock_db_connection() -> MagicMock:
    """Fixture for mocking a DatabaseConnection."""
    conn = MagicMock(spec=DatabaseConnection)
    conn.execute.return_value.fetchdf.return_value = pd.DataFrame()  # Default empty DataFrame
    return conn


@pytest.fixture
def mock_get_connection(mock_db_connection: MagicMock) -> MagicMock:
    """Fixture for mocking the get_connection context manager."""
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_db_connection
    mock_context.__exit__.return_value = None

    def _get_connection():
        return mock_context

    return _get_connection


def test_financial_analysis_initialization(financial_analysis: FinancialAnalysis) -> None:
    """Test the initialization of the FinancialAnalysis class."""
    assert financial_analysis.name == "Financial Analysis"
    assert financial_analysis.description == "Analyzes financial data for significant changes and material events."
    assert financial_analysis.config_section == "financial_analysis"
    assert financial_analysis.requires_db is True
    assert financial_analysis.enable_llm is False
    assert isinstance(financial_analysis.logger, logging.Logger)


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_sync_current_universe_success(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                       mock_db_connection: MagicMock) -> None:
    """Test successful synchronization of the current universe."""
    md_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock MotherDuck data
    md_conn.execute.return_value.fetchdf.return_value = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "name": ["Apple Inc.", "Microsoft Corp"],
            "sector": ["Technology", "Technology"],
            "industry": ["Consumer Electronics", "Software"],
        },
    )

    financial_analysis.sync_current_universe(mock_db_connection, md_conn)

    # Assert that the correct SQL queries were executed
    assert mock_db_connection.execute.call_count == 4
    mock_db_connection.execute.assert_any_call(
        """
                CREATE TABLE IF NOT EXISTS current_universe (
                    ticker VARCHAR PRIMARY KEY, name VARCHAR, sector VARCHAR, industry VARCHAR
                )
            """,
    )
    mock_db_connection.execute.assert_any_call("DELETE FROM current_universe")
    mock_db_connection.execute.assert_any_call("INSERT INTO current_universe SELECT * FROM stocks")
    mock_db_connection.commit.assert_called_once()

    # Assert that the logger was called with the correct message
    financial_analysis.logger.info.assert_called_with("Synced 2 stocks to current_universe table")


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_sync_current_universe_no_motherduck(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                             mock_db_connection: MagicMock) -> None:
    """Test synchronization when no MotherDuck connection is available."""
    financial_analysis.sync_current_universe(mock_db_connection, None)
    financial_analysis.logger.warning.assert_called_with("No MotherDuck connection available, skipping sync")
    mock_db_connection.execute.assert_not_called()


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_sync_current_universe_error(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                     mock_db_connection: MagicMock) -> None:
    """Test synchronization when an error occurs during the process."""
    md_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock an error during MotherDuck data retrieval
    md_conn.execute.side_effect = Exception("Failed to retrieve data")

    with pytest.raises(Exception, match="Failed to retrieve data"):
        financial_analysis.sync_current_universe(mock_db_connection, md_conn)

    financial_analysis.logger.exception.assert_called_once()


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_get_current_universe_success(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                      mock_db_connection: MagicMock) -> None:
    """Test successful retrieval of the current universe of stocks."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock database data
    mock_db_connection.execute.return_value.fetchdf.return_value = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "name": ["Apple Inc.", "Microsoft Corp"],
            "sector": ["Technology", "Technology"],
            "industry": ["Consumer Electronics", "Software"],
        },
    )

    stocks = financial_analysis.get_current_universe()

    # Assert that the correct SQL query was executed
    mock_db_connection.execute.assert_called_once()

    # Assert that the returned data is correct
    assert stocks == [
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
        {"ticker": "MSFT", "name": "Microsoft Corp", "sector": "Technology", "industry": "Software"},
    ]


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_get_current_universe_empty(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                    mock_db_connection: MagicMock) -> None:
    """Test retrieval of the current universe when the database is empty."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock an empty DataFrame
    mock_db_connection.execute.return_value.fetchdf.return_value = pd.DataFrame()

    stocks = financial_analysis.get_current_universe()

    # Assert that the correct SQL query was executed
    mock_db_connection.execute.assert_called_once()

    # Assert that an empty list is returned
    assert stocks == []


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_get_current_universe_error(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                    mock_db_connection: MagicMock) -> None:
    """Test retrieval of the current universe when an error occurs."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock an error during database query
    mock_db_connection.execute.side_effect = Exception("Failed to query database")

    with pytest.raises(Exception, match="Failed to query database"):
        financial_analysis.get_current_universe()

    financial_analysis.logger.exception.assert_called_once()


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_analyze_financial_changes_success(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                           mock_db_connection: MagicMock) -> None:
    """Test successful analysis of financial changes for a given ticker."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock database data
    mock_db_connection.execute.return_value.fetchdf.return_value = pd.DataFrame(
        {
            "metric_name": ["Assets", "Revenues"],
            "current_value": [1200000000.0, 600000000.0],
            "prev_value": [1000000000.0, 500000000.0],
            "end_date": [datetime.now(), datetime.now()],
            "filed_date": [datetime.now(), datetime.now()],
            "pct_change": [20.0, 20.0],
        },
    )

    ticker = "AAPL"
    changes = financial_analysis.analyze_financial_changes(ticker)

    # Assert that the correct SQL query was executed
    mock_db_connection.execute.assert_called_once()

    # Assert that the returned data is correct
    assert len(changes) == 2
    assert changes[0]["metric_name"] == "Assets"
    assert changes[0]["current_value"] == 1200000000.0
    assert changes[0]["prev_value"] == 1000000000.0
    assert changes[0]["pct_change"] == 20.0


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_analyze_financial_changes_no_significant_changes(mock_get_connection: MagicMock,
                                                          financial_analysis: FinancialAnalysis,
                                                          mock_db_connection: MagicMock) -> None:
    """Test analysis of financial changes when no significant changes are found."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock an empty DataFrame
    mock_db_connection.execute.return_value.fetchdf.return_value = pd.DataFrame()

    ticker = "AAPL"
    changes = financial_analysis.analyze_financial_changes(ticker)

    # Assert that the correct SQL query was executed
    mock_db_connection.execute.assert_called_once()

    # Assert that an empty list is returned
    assert changes == []


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_analyze_financial_changes_error(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                         mock_db_connection: MagicMock) -> None:
    """Test analysis of financial changes when an error occurs."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock an error during database query
    mock_db_connection.execute.side_effect = Exception("Failed to query database")

    ticker = "AAPL"
    with pytest.raises(Exception, match="Failed to query database"):
        financial_analysis.analyze_financial_changes(ticker)

    financial_analysis.logger.exception.assert_called_once()


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_analyze_material_events_success(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                        mock_db_connection: MagicMock) -> None:
    """Test successful analysis of material events for a given ticker."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock database data for financial changes
    financial_changes_df = pd.DataFrame(
        {
            "metric_name": ["Assets", "Revenues"],
            "current_value": [1500000000.0, 750000000.0],
            "prev_value": [1000000000.0, 500000000.0],
            "end_date": [datetime.now(), datetime.now()],
            "filed_date": [datetime.now(), datetime.now()],
            "pct_change": [50.0, 50.0],
        },
    )
    mock_db_connection.execute.return_value.fetchdf.side_effect = [financial_changes_df, pd.DataFrame()]

    ticker = "AAPL"
    events = financial_analysis.analyze_material_events(ticker)

    # Assert that the correct SQL queries were executed
    assert mock_db_connection.execute.call_count == 2

    # Assert that the returned data is correct
    assert len(events) == 2
    assert "MAJOR CHANGE: Assets increased by 50.0%" in events[0]
    assert "MAJOR CHANGE: Revenues increased by 50.0%" in events[1]


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_analyze_material_events_no_events(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                         mock_db_connection: MagicMock) -> None:
    """Test analysis of material events when no events are found."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock empty DataFrames for both financial changes and material events
    mock_db_connection.execute.return_value.fetchdf.side_effect = [pd.DataFrame(), pd.DataFrame()]

    ticker = "AAPL"
    events = financial_analysis.analyze_material_events(ticker)

    # Assert that the correct SQL queries were executed
    assert mock_db_connection.execute.call_count == 2

    # Assert that an empty list is returned
    assert events == []


@patch("dewey.core.research.analysis.financial_analysis.get_connection")
def test_analyze_material_events_error(mock_get_connection: MagicMock, financial_analysis: FinancialAnalysis,
                                      mock_db_connection: MagicMock) -> None:
    """Test analysis of material events when an error occurs."""
    mock_get_connection.return_value.__enter__.return_value = mock_db_connection
    mock_get_connection.return_value.__exit__.return_value = None

    # Mock an error during database query
    mock_db_connection.execute.side_effect = Exception("Failed to query database")

    ticker = "AAPL"
    with pytest.raises(Exception, match="Failed to query database"):
        financial_analysis.analyze_material_events(ticker)

    financial_analysis.logger.exception.assert_called_once()


@patch("dewey.core.research.analysis.financial_analysis.FinancialAnalysis.get_current_universe")
@patch("dewey.core.research.analysis.financial_analysis.FinancialAnalysis.analyze_material_events")
def test_run_success(mock_analyze_material_events: MagicMock, mock_get_current_universe: MagicMock,
                   financial_analysis: FinancialAnalysis) -> None:
    """Test successful execution of the run method."""
    # Mock the current universe
    mock_get_current_universe.return_value = [
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
        {"ticker": "MSFT", "name": "Microsoft Corp", "sector": "Technology", "industry": "Software"},
    ]

    # Mock material events
    mock_analyze_material_events.return_value = ["Major event for AAPL"]

    financial_analysis.run()

    # Assert that the correct methods were called
    mock_get_current_universe.assert_called_once()
    assert mock_analyze_material_events.call_count == 2

    # Assert that the logger was called with the correct messages
    financial_analysis.logger.info.assert_any_call("Found 2 stocks in current universe")
    financial_analysis.logger.info.assert_any_call("\nAnalysis completed successfully")


@patch("dewey.core.research.analysis.financial_analysis.FinancialAnalysis.get_current_universe")
@patch("dewey.core.research.analysis.financial_analysis.FinancialAnalysis.analyze_material_events")
def test_run_no_material_findings(mock_analyze_material_events: MagicMock, mock_get_current_universe: MagicMock,
                                 financial_analysis: FinancialAnalysis) -> None:
    """Test execution of the run method when no material findings are found."""
    # Mock the current universe
    mock_get_current_universe.return_value = [
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
    ]

    # Mock no material events
    mock_analyze_material_events.return_value = []

    financial_analysis.run()

    # Assert that the correct methods were called
    mock_get_current_universe.assert_called_once()
    mock_analyze_material_events.assert_called_once()

    # Assert that the logger was called with the correct messages
    financial_analysis.logger.info.assert_any_call("No material findings to report")
    financial_analysis.logger.info.assert_any_call("\nAnalysis completed successfully")


@patch("dewey.core.research.analysis.financial_analysis.FinancialAnalysis.get_current_universe")
def test_run_error(mock_get_current_universe: MagicMock, financial_analysis: FinancialAnalysis) -> None:
    """Test execution of the run method when an error occurs."""
    # Mock an error during retrieval of the current universe
    mock_get_current_universe.side_effect = Exception("Failed to get current universe")

    with pytest.raises(Exception, match="Failed to get current universe"):
        financial_analysis.run()

    financial_analysis.logger.exception.assert_called_once()


def test_get_path(financial_analysis: FinancialAnalysis) -> None:
    """Test the get_path method."""
    # Test with a relative path
    relative_path = "data/test.txt"
    expected_path = financial_analysis.PROJECT_ROOT / relative_path
    assert financial_analysis.get_path(relative_path) == expected_path

    # Test with an absolute path
    absolute_path = "/tmp/test.txt"
    assert financial_analysis.get_path(absolute_path) == Path(absolute_path)


def test_get_config_value(financial_analysis: FinancialAnalysis) -> None:
    """Test the get_config_value method."""
    # Mock the config attribute
    financial_analysis.config = {
        "level1": {
            "level2": {
                "value": "test_value",
            },
        },
    }

    # Test retrieving an existing value
    assert financial_analysis.get_config_value("level1.level2.value") == "test_value"

    # Test retrieving a non-existing value with a default
    assert financial_analysis.get_config_value("level1.level2.non_existing", "default_value") == "default_value"

    # Test retrieving a non-existing value without a default
    assert financial_analysis.get_config_value("level1.non_existing") is None

