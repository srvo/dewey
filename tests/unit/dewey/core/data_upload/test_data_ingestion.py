import logging
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.data_upload.data_ingestion import DataIngestion
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class TestDataIngestion:
    """Unit tests for the DataIngestion class."""

    @pytest.fixture
    def data_ingestion(self) -> DataIngestion:
        """Fixture to create a DataIngestion instance."""
        return DataIngestion()

    @pytest.fixture
    def mock_base_script(self, mocker):
        """Fixture to mock BaseScript methods."""
        mocker.patch("dewey.core.data_upload.data_ingestion.BaseScript.__init__", return_value=None)
        mocker.patch("dewey.core.data_upload.data_ingestion.BaseScript._setup_logging")
        mocker.patch("dewey.core.data_upload.data_ingestion.BaseScript._load_config")
        mocker.patch("dewey.core.data_upload.data_ingestion.BaseScript._initialize_db_connection")
        mocker.patch("dewey.core.data_upload.data_ingestion.BaseScript._initialize_llm_client")

    @pytest.fixture
    def mock_db_connection(self) -> MagicMock:
        """Fixture to mock a database connection."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Fixture to mock an LLM client."""
        return MagicMock(spec=LLMClient)

    def test_init(self, mock_base_script) -> None:
        """Test the __init__ method of DataIngestion."""
        ingestion = DataIngestion()
        assert ingestion.config_section == 'data_ingestion'
        assert ingestion.requires_db is True
        assert ingestion.enable_llm is True

    @patch("dewey.core.data_upload.data_ingestion.BaseScript.get_config_value")
    def test_run_success(
        self,
        mock_get_config_value: MagicMock,
        data_ingestion: DataIngestion,
        mock_db_connection: MagicMock,
        mock_llm_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method with successful data ingestion."""
        mock_get_config_value.side_effect = lambda key, default: {
            'input_path': '/test/input',
            'output_path': '/test/output',
        }.get(key, default)

        data_ingestion.db_conn = mock_db_connection
        data_ingestion.llm_client = mock_llm_client

        with caplog.at_level(logging.INFO):
            data_ingestion.run()

        assert "Starting data ingestion from /test/input to /test/output" in caplog.text
        assert "Database connection is available." in caplog.text
        assert "LLM client is available." in caplog.text
        assert "Data ingestion process completed successfully." in caplog.text

    @patch("dewey.core.data_upload.data_ingestion.BaseScript.get_config_value")
    def test_run_no_db_or_llm(
        self,
        mock_get_config_value: MagicMock,
        data_ingestion: DataIngestion,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method when no database or LLM is available."""
        mock_get_config_value.side_effect = lambda key, default: {
            'input_path': '/test/input',
            'output_path': '/test/output',
        }.get(key, default)

        data_ingestion.db_conn = None
        data_ingestion.llm_client = None

        with caplog.at_level(logging.WARNING):
            data_ingestion.run()

        assert "No database connection available." in caplog.text
        assert "No LLM client available." in caplog.text

    @patch("dewey.core.data_upload.data_ingestion.BaseScript.get_config_value")
    def test_run_exception(
        self,
        mock_get_config_value: MagicMock,
        data_ingestion: DataIngestion,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method when an exception occurs."""
        mock_get_config_value.side_effect = Exception("Test exception")

        with caplog.at_level(logging.ERROR):
            data_ingestion.run()

        assert "An error occurred during data ingestion: Test exception" in caplog.text
        assert "Traceback" in caplog.text

    @patch("dewey.core.data_upload.data_ingestion.DataIngestion.execute")
    def test_main(self, mock_execute: MagicMock) -> None:
        """Test the main execution block."""
        with patch("dewey.core.data_upload.data_ingestion.DataIngestion") as MockDataIngestion:
            # Simulate running the script from the command line
            import dewey.core.data_upload.data_ingestion
            dewey.core.data_upload.data_ingestion.main()

            # Assert that DataIngestion was instantiated and execute was called
            MockDataIngestion.assert_called_once()
            mock_execute.assert_called_once()
