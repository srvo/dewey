import datetime
import os
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest
import requests
from dotenv import load_dotenv

from dewey.core.research.port.tick_processor import (
    DUCKDB_PATH,
    POLYGON_API_KEY,
    SCHEMA,
    TABLE_NAME,
    TICK_API_URL,
    TickProcessor,
)


@pytest.fixture
def tick_processor() -> TickProcessor:
    """Fixture to create a TickProcessor instance."""
    with patch.dict(os.environ, {"POLYGON_API_KEY": "test_api_key"}):
        processor = TickProcessor()
    return processor


@pytest.fixture
def mock_polygon_response() -> Dict[str, Any]:
    """Fixture to create a mock Polygon.io API response."""
    return {
        "status": "OK",
        "results": [
            {
                "T": 1672623600000,
                "p": 170.34,
                "s": 100,
                "c": ["@", "I"],
                "t": 12345,
                "q": 1,
            },
            {
                "T": 1672623601000,
                "p": 170.35,
                "s": 50,
                "c": ["@", "I"],
                "t": 12346,
                "q": 2,
            },
        ],
    }


@pytest.fixture
def mock_empty_polygon_response() -> Dict[str, Any]:
    """Fixture to create a mock empty Polygon.io API response."""
    return {"status": "OK", "results": []}


@pytest.fixture
def mock_requests_get(mock_polygon_response: Dict[str, Any]) -> MagicMock:
    """Fixture to mock the requests.get method."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_polygon_response
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_empty_requests_get(mock_empty_polygon_response: Dict[str, Any]) -> MagicMock:
    """Fixture to mock the requests.get method with an empty response."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_empty_polygon_response
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_duckdb_connection() -> MagicMock:
    """Fixture to mock the duckdb.connect method."""
    mock_con = MagicMock()
    return mock_con


class TestTickProcessor:
    """Tests for the TickProcessor class."""

    @patch("requests.get")
    def test_fetch_ticks_success(
        self,
        mock_get: MagicMock,
        tick_processor: TickProcessor,
        mock_polygon_response: Dict[str, Any],
    ) -> None:
        """Test fetching ticks successfully from the Polygon.io API."""
        mock_get.return_value.json.return_value = mock_polygon_response
        mock_get.return_value.raise_for_status.return_value = None

        ticker = "AAPL"
        date = datetime.date(2024, 1, 2)
        ticks = tick_processor._fetch_ticks(ticker, date)

        assert isinstance(ticks, list)
        assert len(ticks) == 2
        assert ticks[0]["T"] == 1672623600000
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_fetch_ticks_no_results(
        self,
        mock_get: MagicMock,
        tick_processor: TickProcessor,
        mock_empty_polygon_response: Dict[str, Any],
    ) -> None:
        """Test fetching ticks when no results are returned from the API."""
        mock_get.return_value.json.return_value = mock_empty_polygon_response
        mock_get.return_value.raise_for_status.return_value = None

        ticker = "AAPL"
        date = datetime.date(2024, 1, 2)
        ticks = tick_processor._fetch_ticks(ticker, date)

        assert isinstance(ticks, list)
        assert len(ticks) == 0
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_fetch_ticks_api_error(
        self, mock_get: MagicMock, tick_processor: TickProcessor
    ) -> None:
        """Test fetching ticks when the API returns an error."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        ticker = "AAPL"
        date = datetime.date(2024, 1, 2)

        with pytest.raises(requests.exceptions.RequestException):
            tick_processor._fetch_ticks(ticker, date)

        mock_get.assert_called_once()

    def test_transform_ticks_success(
        self, tick_processor: TickProcessor, mock_polygon_response: Dict[str, Any]
    ) -> None:
        """Test transforming raw tick data into a Pandas DataFrame."""
        ticker = "AAPL"
        ticks = mock_polygon_response["results"]
        df = tick_processor._transform_ticks(ticks, ticker)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "ticker" in df.columns
        assert "trade_id" in df.columns
        assert "timestamp" in df.columns
        assert "price" in df.columns
        assert "size" in df.columns
        assert "conditions" in df.columns
        assert "sequence_number" in df.columns
        assert df["ticker"][0] == ticker
        assert df["trade_id"][0] == 12345
        assert df["price"][0] == 170.34
        assert df["size"][0] == 100
        assert df["conditions"][0] == "@,I"
        assert df["sequence_number"][0] == 1

    def test_transform_ticks_empty_list(self, tick_processor: TickProcessor) -> None:
        """Test transforming an empty list of ticks."""
        ticker = "AAPL"
        ticks: List[Dict[str, Any]] = []
        df = tick_processor._transform_ticks(ticks, ticker)

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    @patch("duckdb.connect")
    def test_store_ticks_success(
        self, mock_connect: MagicMock, tick_processor: TickProcessor
    ) -> None:
        """Test storing transformed tick data into the DuckDB database."""
        # Create a sample DataFrame
        data = {
            "ticker": ["AAPL", "AAPL"],
            "trade_id": [12345, 12346],
            "timestamp": [
                pd.Timestamp("2023-01-02 16:20:00+00:00"),
                pd.Timestamp("2023-01-02 16:20:01+00:00"),
            ],
            "price": [170.34, 170.35],
            "size": [100, 50],
            "conditions": ["@,I", "@,I"],
            "sequence_number": [1, 2],
        }
        df = pd.DataFrame(data)

        # Mock the duckdb connection and its methods
        mock_con = mock_connect.return_value
        mock_con.execute.return_value = None
        mock_con.register.return_value = None
        mock_con.close.return_value = None

        # Call the _store_ticks method
        tick_processor._store_ticks(df)

        # Assert that the mock methods were called with the correct arguments
        mock_connect.assert_called_once_with(DUCKDB_PATH)
        mock_con.execute.assert_called_with("SET timezone='UTC'")
        mock_con.register.assert_called_with("tick_data", df)
        mock_con.execute.assert_called_with(
            f"""
                INSERT INTO {TABLE_NAME}
                SELECT ticker, trade_id, timestamp, price, size, conditions, sequence_number
                FROM tick_data
            """
        )
        mock_con.close.assert_called_once()

    @patch("duckdb.connect")
    def test_store_ticks_empty_dataframe(
        self, mock_connect: MagicMock, tick_processor: TickProcessor
    ) -> None:
        """Test storing an empty DataFrame into the DuckDB database."""
        df = pd.DataFrame()
        tick_processor._store_ticks(df)

        mock_connect.assert_not_called()

    @patch("duckdb.connect")
    def test_store_ticks_database_error(
        self, mock_connect: MagicMock, tick_processor: TickProcessor
    ) -> None:
        """Test storing ticks when a database error occurs."""
        # Create a sample DataFrame
        data = {
            "ticker": ["AAPL", "AAPL"],
            "trade_id": [12345, 12346],
            "timestamp": [
                pd.Timestamp("2023-01-02 16:20:00+00:00"),
                pd.Timestamp("2023-01-02 16:20:01+00:00"),
            ],
            "price": [170.34, 170.35],
            "size": [100, 50],
            "conditions": ["@,I", "@,I"],
            "sequence_number": [1, 2],
        }
        df = pd.DataFrame(data)

        # Mock the duckdb connection and its methods
        mock_con = mock_connect.return_value
        mock_con.execute.side_effect = duckdb.Error("Database error")
        mock_con.close.return_value = None

        # Call the _store_ticks method and assert that it raises an exception
        with pytest.raises(duckdb.Error):
            tick_processor._store_ticks(df)

        # Assert that the mock methods were called with the correct arguments
        mock_connect.assert_called_once_with(DUCKDB_PATH)
        mock_con.execute.assert_called_with("SET timezone='UTC'")
        mock_con.register.assert_called_with("tick_data", df)
        mock_con.close.assert_called_once()

    @patch("dewey.core.research.port.tick_processor.TickProcessor._fetch_ticks")
    @patch("dewey.core.research.port.tick_processor.TickProcessor._transform_ticks")
    @patch("dewey.core.research.port.tick_processor.TickProcessor._store_ticks")
    def test_run_success(
        self,
        mock_store_ticks: MagicMock,
        mock_transform_ticks: MagicMock,
        mock_fetch_ticks: MagicMock,
        tick_processor: TickProcessor,
    ) -> None:
        """Test the run method successfully processes and stores ticks."""
        # Arrange
        mock_fetch_ticks.return_value = [{"tick": "data"}]
        mock_transform_ticks.return_value = pd.DataFrame({"tick": ["data"]})
        mock_store_ticks.return_value = None

        # Act
        tick_processor.run()

        # Assert
        mock_fetch_ticks.assert_called_once()
        mock_transform_ticks.assert_called_once()
        mock_store_ticks.assert_called_once()

    @patch("dewey.core.research.port.tick_processor.TickProcessor._fetch_ticks")
    @patch("dewey.core.research.port.tick_processor.TickProcessor._transform_ticks")
    @patch("dewey.core.research.port.tick_processor.TickProcessor._store_ticks")
    def test_run_no_data_to_store(
        self,
        mock_store_ticks: MagicMock,
        mock_transform_ticks: MagicMock,
        mock_fetch_ticks: MagicMock,
        tick_processor: TickProcessor,
    ) -> None:
        """Test the run method handles the case where there is no data to store after transformation."""
        # Arrange
        mock_fetch_ticks.return_value = [{"tick": "data"}]
        mock_transform_ticks.return_value = pd.DataFrame()  # Empty DataFrame
        mock_store_ticks.return_value = None

        # Act
        tick_processor.run()

        # Assert
        mock_fetch_ticks.assert_called_once()
        mock_transform_ticks.assert_called_once()
        mock_store_ticks.assert_not_called()  # Ensure _store_ticks is not called

    @patch("dewey.core.research.port.tick_processor.TickProcessor._fetch_ticks")
    @patch("dewey.core.research.port.tick_processor.TickProcessor._transform_ticks")
    @patch("dewey.core.research.port.tick_processor.TickProcessor._store_ticks")
    def test_run_exception_handling(
        self,
        mock_store_ticks: MagicMock,
        mock_transform_ticks: MagicMock,
        mock_fetch_ticks: MagicMock,
        tick_processor: TickProcessor,
    ) -> None:
        """Test the run method handles exceptions during processing."""
        # Arrange
        mock_fetch_ticks.side_effect = Exception("Simulated error")

        # Act & Assert
        with pytest.raises(Exception, match="Simulated error"):
            tick_processor.run()

        # Assert that other methods were not called after the exception
        mock_transform_ticks.assert_not_called()
        mock_store_ticks.assert_not_called()
