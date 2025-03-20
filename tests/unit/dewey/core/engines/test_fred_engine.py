import pytest
from unittest.mock import MagicMock, patch
from dewey.core.engines.fred_engine import FredEngine
import logging
from dewey.core.db.connection import DatabaseConnection


class TestFredEngine:
    """
    Comprehensive unit tests for the FredEngine class, covering initialization,
    configuration, database interaction, LLM integration, and error handling.
    """

    @pytest.fixture
    def fred_engine(self) -> FredEngine:
        """
        Pytest fixture to create an instance of FredEngine with mocked dependencies.

        Returns:
            FredEngine: An instance of FredEngine.
        """
        with patch('dewey.core.engines.fred_engine.BaseScript.__init__') as mock_base_init:
            mock_base_init.return_value=None, fred_engine: FredEngine) -> None:
        """
        Test the initialization of the FredEngine class.
        """
        assert fred_engine.name == "FredEngine"
        assert fred_engine.config_section == 'fred_engine'
        assert fred_engine.requires_db is True
        assert fred_engine.enable_llm is True

    def test_run_success_no_db_no_llm(self, fred_engine: FredEngine) -> None:
        """
        Test the successful execution of the run method without database and LLM.
        """
        fred_engine.db_conn = None
        fred_engine.llm_client = None
        fred_engine.config = {'example_config': 'test_value'}

        fred_engine.get_config_value = MagicMock(return_value='test_value')

        fred_engine.run()

        fred_engine.logger.info.assert_called()
        fred_engine.get_config_value.assert_called_with('example_config', 'default_value')
        fred_engine.logger.warning.assert_called()

    def test_run_success_with_db_and_llm(self, fred_engine: FredEngine) -> None:
        """
        Test the successful execution of the run method with database and LLM.
        """
        # Mock database connection and cursor
        mock_db_conn = MagicMock(spec=DatabaseConnection)
        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        fred_engine.db_conn = mock_db_conn

        # Mock LLM client and response
        mock_llm_client = MagicMock()
        mock_llm_utils = MagicMock()
        mock_llm_utils.generate_response.return_value = "A poem about Fred."
        fred_engine.llm_client = mock_llm_client

        # Patch llm_utils.generate_response to use the mock
        with patch('dewey.core.engines.fred_engine.llm_utils', mock_llm_utils):
            if self) -> FredEngine:
        """
        Pytest fixture to create an instance of FredEngine with mocked dependencies.

        Returns:
            FredEngine: An instance of FredEngine.
        """
        with patch('dewey.core.engines.fred_engine.BaseScript.__init__') as mock_base_init:
            mock_base_init.return_value is None:
                self) -> FredEngine:
        """
        Pytest fixture to create an instance of FredEngine with mocked dependencies.

        Returns:
            FredEngine: An instance of FredEngine.
        """
        with patch('dewey.core.engines.fred_engine.BaseScript.__init__') as mock_base_init:
            mock_base_init.return_value = None  # Mock the base class initialization
            engine = FredEngine()
            engine.logger = MagicMock(spec=logging.Logger)  # Mock the logger
            engine.config = {}  # Mock the config
            engine.db_conn = None  # Mock the db_conn
            engine.llm_client = None  # Mock the llm_client
            return engine

    def test_fred_engine_initialization(self
            fred_engine.run()

        # Assertions
        fred_engine.logger.info.assert_called()
        mock_db_conn.cursor.assert_called()
        mock_cursor.execute.assert_called_with("SELECT 1")
        mock_cursor.fetchone.assert_called()
        mock_llm_utils.generate_response.assert_called_with(mock_llm_client, "Write a short poem about Fred.")

    def test_run_exception(self, fred_engine: FredEngine) -> None:
        """
        Test the exception handling in the run method.
        """
        fred_engine.get_config_value = MagicMock(side_effect=Exception("Test Exception"))

        with pytest.raises(Exception, match="Test Exception"):
            fred_engine.run()

        fred_engine.logger.error.assert_called()

    def test_run_no_db_connection(self, fred_engine: FredEngine) -> None:
        """
        Test the scenario when the database connection is not available.
        """
        fred_engine.db_conn = None
        fred_engine.llm_client = MagicMock()
        fred_engine.get_config_value = MagicMock(return_value='test_value')

        fred_engine.run()

        fred_engine.logger.warning.assert_called_with("Database connection is not available.")

    def test_run_no_llm_client(self, fred_engine: FredEngine) -> None:
        """
        Test the scenario when the LLM client is not available.
        """
        fred_engine.db_conn = MagicMock()
        fred_engine.llm_client = None
        fred_engine.get_config_value = MagicMock(return_value='test_value')

        fred_engine.run()

        fred_engine.logger.warning.assert_called_with("LLM client is not available.")
