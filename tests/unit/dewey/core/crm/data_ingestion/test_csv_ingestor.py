import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.data_ingestion.csv_ingestor import CsvIngestor


class TestCsvIngestor:
    """Unit tests for the CsvIngestor class."""

    @pytest.fixture
    def csv_ingestor(self) -> CsvIngestor:
        """Fixture to create a CsvIngestor instance."""
        return CsvIngestor()

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript methods."""
        mock = MagicMock(spec=BaseScript)
        mock.logger = MagicMock(spec=logging.Logger)
        mock.get_config_value.return_value = "test_value"  # Default config value
        mock.db_conn = MagicMock()
        mock.db_conn.cursor.return_value.__enter__.return_value = MagicMock()
        return mock

    @patch(
        "dewey.core.crm.data_ingestion.csv_ingestor.CsvIngestor.__init__",
        return_value=None,
    )
    def test_init(self, mock_init: MagicMock) -> None:
        """Test the __init__ method."""
        ingestor = CsvIngestor()
        mock_init.assert_called_once()

    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.__init__")
    def test_init_base_script_called(self, mock_base_init: MagicMock) -> None:
        """Test that BaseScript.__init__ is called with correct arguments."""
        CsvIngestor()
        mock_base_init.assert_called_once_with(
            config_section="csv_ingestor", requires_db=True
        )

    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.get_config_value")
    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.db_conn")
    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.logger")
    def test_run_success(
        self,
        mock_logger: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        csv_ingestor: CsvIngestor,
    ) -> None:
        """Test the run method with successful CSV ingestion."""
        mock_get_config_value.side_effect = ["test_csv_path", "test_table_name"]
        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor

        csv_ingestor.run()

        mock_logger.info.assert_called()
        assert mock_get_config_value.call_count == 2
        mock_db_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_not_called()  # No actual SQL execution in this test

    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.get_config_value")
    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.logger")
    def test_run_missing_config(
        self,
        mock_logger: MagicMock,
        mock_get_config_value: MagicMock,
        csv_ingestor: CsvIngestor,
    ) -> None:
        """Test the run method when configuration values are missing."""
        mock_get_config_value.side_effect = [None, None]

        with pytest.raises(ValueError) as exc_info:
            csv_ingestor.run()

        assert (
            "CSV file path and table name must be specified in the configuration."
            in str(exc_info.value)
        )
        mock_logger.error.assert_not_called()

    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.get_config_value")
    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.db_conn")
    @patch("dewey.core.crm.data_ingestion.csv_ingestor.BaseScript.logger")
    def test_run_exception(
        self,
        mock_logger: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        csv_ingestor: CsvIngestor,
    ) -> None:
        """Test the run method when an exception occurs during ingestion."""
        mock_get_config_value.side_effect = ["test_csv_path", "test_table_name"]
        mock_db_conn.cursor.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            csv_ingestor.run()

        assert "Database error" in str(exc_info.value)
        mock_logger.error.assert_called()
