import pytest
from unittest.mock import MagicMock, patch
from dewey.core.research.companies.companies import Companies
from dewey.core.base_script import BaseScript
import logging


class TestCompanies:
    """Tests for the Companies class."""

    @pytest.fixture
    def companies(self) -> Companies:
        """Fixture for creating a Companies instance."""
        return Companies()

    def test_companies_initialization(self, companies: Companies) -> None:
        """Test that Companies initializes correctly."""
        assert isinstance(companies, Companies)
        assert isinstance(companies, BaseScript)
        assert companies.config_section == "companies"
        assert companies.requires_db is True
        assert companies.enable_llm is True
        assert isinstance(companies.logger, logging.Logger)
        assert companies.config is not None
        assert companies.db_conn is None  # Not initialized until run
        assert companies.llm_client is None  # Not initialized until run

    @patch("dewey.core.research.companies.companies.execute_query")
    @patch("dewey.core.research.companies.companies.generate_text")
    def test_run_success(
        self,
        mock_generate_text: MagicMock,
        mock_execute_query: MagicMock,
        companies: Companies,
    ) -> None:
        """Test successful execution of the run method."""
        # Mock dependencies
        mock_execute_query.return_value = [
            {"ticker": "AAPL"},
            {"ticker": "GOOG"},
        ]
        mock_generate_text.return_value = "Technology company summary"

        # Mock logger info to capture log messages
        companies.logger.info = MagicMock()  # type: ignore

        # Call the run method
        companies.run()

        # Assertions
        mock_execute_query.assert_called_once()
        mock_generate_text.assert_called_once()
        companies.logger.info.assert_called()  # type: ignore
        assert "Starting company research and analysis..." in str(
            companies.logger.info.call_args_list  # type: ignore
        )
        assert "Company research and analysis completed." in str(
            companies.logger.info.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.execute_query")
    @patch("dewey.core.research.companies.companies.generate_text")
    def test_run_api_url_config(
        self,
        mock_generate_text: MagicMock,
        mock_execute_query: MagicMock,
        companies: Companies,
    ) -> None:
        """Test that the API URL is loaded from the config."""
        # Mock dependencies
        mock_execute_query.return_value = []
        mock_generate_text.return_value = ""

        # Mock logger
        companies.logger.debug = MagicMock()  # type: ignore

        # Mock config to return a specific API URL
        companies.get_config_value = MagicMock(return_value="http://test-api.com")  # type: ignore

        # Call the run method
        companies.run()

        # Assertions
        companies.logger.debug.assert_called()  # type: ignore
        assert "API URL: http://test-api.com" in str(
            companies.logger.debug.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.execute_query")
    @patch("dewey.core.research.companies.companies.generate_text")
    def test_run_database_interaction(
        self,
        mock_generate_text: MagicMock,
        mock_execute_query: MagicMock,
        companies: Companies,
    ) -> None:
        """Test database interaction within the run method."""
        # Mock dependencies
        mock_execute_query.return_value = [
            {"ticker": "AAPL"},
            {"ticker": "GOOG"},
        ]
        mock_generate_text.return_value = "Technology company summary"

        # Call the run method
        companies.run()

        # Assertions
        mock_execute_query.assert_called_once()
        mock_execute_query.assert_called_with(
            companies.db_conn, "SELECT * FROM companies LIMIT 10;"
        )

    @patch("dewey.core.research.companies.companies.execute_query")
    @patch("dewey.core.research.companies.companies.generate_text")
    def test_run_llm_interaction(
        self,
        mock_generate_text: MagicMock,
        mock_execute_query: MagicMock,
        companies: Companies,
    ) -> None:
        """Test LLM interaction within the run method."""
        # Mock dependencies
        mock_execute_query.return_value = []
        mock_generate_text.return_value = "Technology company summary"
        companies.llm_client = MagicMock()

        # Call the run method
        companies.run()

        # Assertions
        mock_generate_text.assert_called_once()
        mock_generate_text.assert_called_with(
            companies.llm_client,
            "Summarize the key activities of a technology company.",
        )

    @patch("dewey.core.research.companies.companies.execute_query")
    @patch("dewey.core.research.companies.companies.generate_text")
    def test_run_exception_handling(
        self,
        mock_generate_text: MagicMock,
        mock_execute_query: MagicMock,
        companies: Companies,
    ) -> None:
        """Test exception handling within the run method."""
        # Mock dependencies
        mock_execute_query.side_effect = Exception("Database error")

        # Mock logger
        companies.logger.error = MagicMock()  # type: ignore

        # Call the run method and assert that it raises an exception
        with pytest.raises(Exception) as exc_info:
            companies.run()

        # Assertions
        assert "Database error" in str(exc_info.value)
        companies.logger.error.assert_called()  # type: ignore
        assert "An error occurred: Database error" in str(
            companies.logger.error.call_args_list  # type: ignore
        )

    def test_get_config_value_existing_key(self, companies: Companies) -> None:
        """Test getting an existing config value."""
        companies.config = {"level1": {"level2": "value"}}
        value = companies.get_config_value("level1.level2")
        assert value == "value"

    def test_get_config_value_missing_key(self, companies: Companies) -> None:
        """Test getting a missing config value with a default."""
        companies.config = {"level1": {"level2": "value"}}
        value = companies.get_config_value("level1.level3", "default")
        assert value == "default"

    def test_get_config_value_missing_key_no_default(
        self, companies: Companies
    ) -> None:
        """Test getting a missing config value without a default."""
        companies.config = {"level1": {"level2": "value"}}
        value = companies.get_config_value("level1.level3")
        assert value is None

    def test_get_config_value_non_dict_intermediate(self, companies: Companies) -> None:
        """Test when an intermediate level is not a dictionary."""
        companies.config = {"level1": "not_a_dict"}
        value = companies.get_config_value("level1.level2", "default")
        assert value == "default"

    @patch("dewey.core.research.companies.companies.Path.exists")
    @patch("dewey.core.research.companies.companies.yaml.safe_load")
    def test_parse_args_config_override(
        self,
        mock_safe_load: MagicMock,
        mock_path_exists: MagicMock,
        companies: Companies,
    ) -> None:
        """Test that command line arguments override config values."""
        # Mock command line arguments
        companies.setup_argparse = MagicMock()
        parser_mock = MagicMock()
        companies.setup_argparse.return_value = parser_mock
        args_mock = MagicMock()
        args_mock.config = "test_config.yaml"
        args_mock.log_level = None
        args_mock.db_connection_string = None
        args_mock.llm_model = None
        parser_mock.parse_args.return_value = args_mock

        # Mock file existence and content
        mock_path_exists.return_value = True
        mock_safe_load.return_value = {"test": "value"}

        # Call parse_args
        args = companies.parse_args()

        # Assertions
        assert companies.config == {"test": "value"}
        companies.logger.info = MagicMock()  # type: ignore
        companies.parse_args()
        companies.logger.info.assert_called()  # type: ignore
        assert "Loaded configuration from test_config.yaml" in str(
            companies.logger.info.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.logging")
    def test_parse_args_log_level_override(
        self, mock_logging: MagicMock, companies: Companies
    ) -> None:
        """Test that command line arguments override log level."""
        # Mock command line arguments
        companies.setup_argparse = MagicMock()
        parser_mock = MagicMock()
        companies.setup_argparse.return_value = parser_mock
        args_mock = MagicMock()
        args_mock.config = None
        args_mock.log_level = "DEBUG"
        args_mock.db_connection_string = None
        args_mock.llm_model = None
        parser_mock.parse_args.return_value = args_mock

        # Call parse_args
        companies.parse_args()

        # Assertions
        companies.logger.setLevel.assert_called_with(logging.DEBUG)  # type: ignore
        companies.logger.debug = MagicMock()  # type: ignore
        companies.parse_args()
        companies.logger.debug.assert_called()  # type: ignore
        assert "Log level set to DEBUG" in str(
            companies.logger.debug.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.get_connection")
    def test_parse_args_db_connection_override(
        self, mock_get_connection: MagicMock, companies: Companies
    ) -> None:
        """Test that command line arguments override database connection string."""
        # Mock command line arguments
        companies.setup_argparse = MagicMock()
        parser_mock = MagicMock()
        companies.setup_argparse.return_value = parser_mock
        args_mock = MagicMock()
        args_mock.config = None
        args_mock.log_level = None
        args_mock.db_connection_string = "custom_connection_string"
        args_mock.llm_model = None
        parser_mock.parse_args.return_value = args_mock
        companies.requires_db = True

        # Call parse_args
        companies.parse_args()

        # Assertions
        mock_get_connection.assert_called_with(
            {"connection_string": "custom_connection_string"}
        )
        companies.logger.info = MagicMock()  # type: ignore
        companies.parse_args()
        companies.logger.info.assert_called()  # type: ignore
        assert "Using custom database connection" in str(
            companies.logger.info.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.get_llm_client")
    def test_parse_args_llm_model_override(
        self, mock_get_llm_client: MagicMock, companies: Companies
    ) -> None:
        """Test that command line arguments override LLM model."""
        # Mock command line arguments
        companies.setup_argparse = MagicMock()
        parser_mock = MagicMock()
        companies.setup_argparse.return_value = parser_mock
        args_mock = MagicMock()
        args_mock.config = None
        args_mock.log_level = None
        args_mock.db_connection_string = None
        args_mock.llm_model = "custom_llm_model"
        parser_mock.parse_args.return_value = args_mock
        companies.enable_llm = True

        # Call parse_args
        companies.parse_args()

        # Assertions
        mock_get_llm_client.assert_called_with({"model": "custom_llm_model"})
        companies.logger.info = MagicMock()  # type: ignore
        companies.parse_args()
        companies.logger.info.assert_called()  # type: ignore
        assert "Using custom LLM model: custom_llm_model" in str(
            companies.logger.info.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.Path.exists")
    def test_parse_args_config_not_found(
        self, mock_path_exists: MagicMock, companies: Companies
    ) -> None:
        """Test that the script exits if the config file is not found."""
        # Mock command line arguments
        companies.setup_argparse = MagicMock()
        parser_mock = MagicMock()
        companies.setup_argparse.return_value = parser_mock
        args_mock = MagicMock()
        args_mock.config = "nonexistent_config.yaml"
        args_mock.log_level = None
        args_mock.db_connection_string = None
        args_mock.llm_model = None
        parser_mock.parse_args.return_value = args_mock

        # Mock file existence
        mock_path_exists.return_value = False

        # Call parse_args and assert that it exits
        with pytest.raises(SystemExit) as exc_info:
            companies.parse_args()

        # Assertions
        assert exc_info.value.code == 1
        companies.logger.error = MagicMock()  # type: ignore
        companies.parse_args()
        companies.logger.error.assert_called()  # type: ignore
        assert "Configuration file not found: nonexistent_config.yaml" in str(
            companies.logger.error.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.BaseScript._cleanup")
    @patch("dewey.core.research.companies.companies.BaseScript.run")
    @patch("dewey.core.research.companies.companies.BaseScript.parse_args")
    def test_execute_success(
        self,
        mock_parse_args: MagicMock,
        mock_run: MagicMock,
        mock_cleanup: MagicMock,
        companies: Companies,
    ) -> None:
        """Test successful execution of the execute method."""
        # Mock dependencies
        mock_parse_args.return_value = MagicMock()

        # Mock logger
        companies.logger.info = MagicMock()  # type: ignore

        # Call the execute method
        companies.execute()

        # Assertions
        mock_parse_args.assert_called_once()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()
        companies.logger.info.assert_called()  # type: ignore
        assert "Starting execution of Companies" in str(
            companies.logger.info.call_args_list  # type: ignore
        )
        assert "Completed execution of Companies" in str(
            companies.logger.info.call_args_list  # type: ignore
        )

    @patch("dewey.core.research.companies.companies.BaseScript._cleanup")
    @patch("dewey.core.research.companies.companies.BaseScript.run")
    @patch("dewey.core.research.companies.companies.BaseScript.parse_args")
    def test_execute_keyboard_interrupt(
        self,
        mock_parse_args: MagicMock,
        mock_run: MagicMock,
        mock_cleanup: MagicMock,
        companies: Companies,
    ) -> None:
        """Test handling of KeyboardInterrupt in the execute method."""
        # Mock dependencies
        mock_parse_args.return_value = MagicMock()
        mock_run.side_effect = KeyboardInterrupt()

        # Mock logger
        companies.logger.warning = MagicMock()  # type: ignore

        # Call the execute method and assert that it exits
        with pytest.raises(SystemExit) as exc_info:
            companies.execute()

        # Assertions
        assert exc_info.value.code == 1
        companies.logger.warning.assert_called()  # type: ignore
        assert "Script interrupted by user" in str(
            companies.logger.warning.call_args_list  # type: ignore
        )
        mock_cleanup.assert_called_once()

    @patch("dewey.core.research.companies.companies.BaseScript._cleanup")
    @patch("dewey.core.research.companies.companies.BaseScript.run")
    @patch("dewey.core.research.companies.companies.BaseScript.parse_args")
    def test_execute_exception(
        self,
        mock_parse_args: MagicMock,
        mock_run: MagicMock,
        mock_cleanup: MagicMock,
        companies: Companies,
    ) -> None:
        """Test handling of exceptions in the execute method."""
        # Mock dependencies
        mock_parse_args.return_value = MagicMock()
        mock_run.side_effect = Exception("Test exception")

        # Mock logger
        companies.logger.error = MagicMock()  # type: ignore

        # Call the execute method and assert that it exits
        with pytest.raises(SystemExit) as exc_info:
            companies.execute()

        # Assertions
        assert exc_info.value.code == 1
        companies.logger.error.assert_called()  # type: ignore
        assert "Error executing script: Test exception" in str(
            companies.logger.error.call_args_list  # type: ignore
        )
        mock_cleanup.assert_called_once()

    def test_cleanup_db_connection_success(self, companies: Companies) -> None:
        """Test successful cleanup of the database connection."""
        # Mock database connection
        companies.db_conn = MagicMock()

        # Call the cleanup method
        companies._cleanup()

        # Assertions
        companies.db_conn.close.assert_called_once()  # type: ignore

    def test_cleanup_db_connection_exception(self, companies: Companies) -> None:
        """Test handling of exceptions during database connection cleanup."""
        # Mock database connection
        companies.db_conn = MagicMock()
        companies.db_conn.close.side_effect = Exception("Close error")  # type: ignore

        # Mock logger
        companies.logger.warning = MagicMock()  # type: ignore

        # Call the cleanup method
        companies._cleanup()

        # Assertions
        companies.db_conn.close.assert_called_once()  # type: ignore
        companies.logger.warning.assert_called()  # type: ignore
        assert "Error closing database connection: Close error" in str(
            companies.logger.warning.call_args_list  # type: ignore
        )

    def test_cleanup_no_db_connection(self, companies: Companies) -> None:
        """Test cleanup when there is no database connection."""
        # Call the cleanup method
        companies._cleanup()

        # Assertions
        # No exceptions should be raised

    def test_get_path_absolute(self, companies: Companies) -> None:
        """Test getting an absolute path."""
        path = companies.get_path("/absolute/path")
        assert str(path) == "/absolute/path"

    def test_get_path_relative(self, companies: Companies) -> None:
        """Test getting a relative path."""
        path = companies.get_path("relative/path")
        assert str(path) == str(companies.PROJECT_ROOT / "relative" / "path")
