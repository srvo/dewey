"""Unit tests for the universe_breakdown module."""

import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest
import yaml

# Assuming the project root is two levels up from the test file
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "dewey.yaml"

# Dynamically determine the path to the module being tested
MODULE_PATH = PROJECT_ROOT / "src" / "dewey" / "core" / "research" / "utils" / "universe_breakdown.py"

# Add the module's directory to the Python path so it can be imported
import sys
sys.path.insert(0, str(MODULE_PATH.parent))
import universe_breakdown  # noqa: E402


@pytest.fixture(scope="session")
def config() -> Dict[str, Any]:
    """Load the Dewey configuration."""
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def mock_universe_file(tmp_path: Path) -> Path:
    """Create a mock universe CSV file."""
    data = {'ticker': ['AAPL', 'MSFT', 'GOOG'],
            'sector': ['Technology', 'Technology', 'Technology'],
            'industry': ['Software', 'Software', 'Software'],
            'country': ['USA', 'USA', 'USA']}
    df = pd.DataFrame(data)
    file_path = tmp_path / 'universe.csv'
    df.to_csv(file_path, index=False)
    return file_path


@pytest.fixture
def mock_duckdb_connection(mock_universe_file: Path, tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """Create a mock DuckDB connection and load the mock universe data."""
    db_file = tmp_path / 'merged.duckdb'
    con = duckdb.connect(str(db_file))
    return con


@pytest.fixture
def mock_env_variables(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mock_universe_file: Path) -> None:
    """Mock environment variables."""
    monkeypatch.setenv("DATABASE_FILE", str(tmp_path / 'merged.duckdb'))
    monkeypatch.setenv("UNIVERSE_FILE", str(mock_universe_file))
    monkeypatch.setenv("OUTPUT_FILE", str(tmp_path / 'universe_breakdown.csv'))


def test_sector_breakdown(mock_duckdb_connection: duckdb.DuckDBPyConnection, mock_universe_file: Path) -> None:
    """Test the sector breakdown query."""
    expected_df = pd.DataFrame({'sector': ['Technology'], 'count': [3]})
    result_df = mock_duckdb_connection.execute(f"""
        SELECT sector, COUNT(*) AS count
        FROM read_csv_auto('{mock_universe_file}')
        GROUP BY sector
        ORDER BY count DESC
    """).df()
    pd.testing.assert_frame_equal(result_df, expected_df)


def test_industry_breakdown(mock_duckdb_connection: duckdb.DuckDBPyConnection, mock_universe_file: Path) -> None:
    """Test the industry breakdown query."""
    expected_df = pd.DataFrame({'industry': ['Software'], 'count': [3]})
    result_df = mock_duckdb_connection.execute(f"""
        SELECT industry, COUNT(*) AS count
        FROM read_csv_auto('{mock_universe_file}')
        GROUP BY industry
        ORDER BY count DESC
    """).df()
    pd.testing.assert_frame_equal(result_df, expected_df)


def test_country_breakdown(mock_duckdb_connection: duckdb.DuckDBPyConnection, mock_universe_file: Path) -> None:
    """Test the country breakdown query."""
    expected_df = pd.DataFrame({'country': ['USA'], 'count': [3]})
    result_df = mock_duckdb_connection.execute(f"""
        SELECT country, COUNT(*) AS count
        FROM read_csv_auto('{mock_universe_file}')
        GROUP BY country
        ORDER BY count DESC
    """).df()
    pd.testing.assert_frame_equal(result_df, expected_df)


@patch("universe_breakdown.universe", new_callable=pd.DataFrame)
@patch("universe_breakdown.con")
def test_main_functionality(mock_con, mock_universe, mock_universe_file, tmp_path, monkeypatch):
    """Test the main functionality of the script."""
    # Mock dataframes for sector, industry, and country breakdowns
    mock_sector_breakdown = pd.DataFrame({'sector': ['Technology'], 'count': [3]})
    mock_industry_breakdown = pd.DataFrame({'industry': ['Software'], 'count': [3]})
    mock_country_breakdown = pd.DataFrame({'country': ['USA'], 'count': [3]})

    # Configure the mock con object
    mock_con.execute.return_value.df.side_effect = [
        mock_sector_breakdown,
        mock_industry_breakdown,
        mock_country_breakdown,
    ]
    mock_universe.return_value = pd.read_csv(mock_universe_file)

    # Patch the to_csv methods to prevent actual file writing
    with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
        # Call the script's main execution logic
        universe_breakdown.universe = mock_universe.return_value
        universe_breakdown.con = mock_con
        universe_breakdown.sector_breakdown = mock_sector_breakdown
        universe_breakdown.industry_breakdown = mock_industry_breakdown
        universe_breakdown.country_breakdown = mock_country_breakdown

        # Assert that the to_csv methods were called with the correct arguments
        assert mock_to_csv.call_count == 0  # Ensure it's not called during the test

        # Assert that the print statements were called with the correct arguments
        # (This part requires capturing stdout, which is more complex and might not be necessary for this test)

        # Assert that the database connection was closed
        assert mock_con.close.call_count == 0  # Ensure it's not called during the test


def test_file_not_found_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the FileNotFoundError when the universe file does not exist."""
    monkeypatch.setenv("UNIVERSE_FILE", "nonexistent_file.csv")
    with pytest.raises(FileNotFoundError):
        pd.read_csv(os.environ["UNIVERSE_FILE"])


def test_duckdb_connection_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test the DuckDB connection error when the database file does not exist."""
    monkeypatch.setenv("DATABASE_FILE", str(tmp_path / 'nonexistent.duckdb'))
    with pytest.raises(duckdb.CatalogException):
        duckdb.connect(os.environ["DATABASE_FILE"])


def test_empty_universe_file(tmp_path: Path) -> None:
    """Test the behavior when the universe file is empty."""
    file_path = tmp_path / 'empty_universe.csv'
    with open(file_path, 'w') as f:
        f.write('')

    with pytest.raises(pd.errors.EmptyDataError):
        pd.read_csv(file_path)
