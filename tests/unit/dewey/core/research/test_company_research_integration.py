import unittest
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.research.company_research_integration import (
    CompanyResearchIntegration,
)


class TestCompanyResearchIntegration(unittest.TestCase):
    """Unit tests for the CompanyResearchIntegration class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.mock_config = {
            "company_research": {"api_key": "test_api_key"},
            "core": {"logging": {"level": "DEBUG"}},
        }
        self.mock_logger = MagicMock()
        self.mock_db_conn = MagicMock()
        self.mock_llm_client = MagicMock()

        # Patching BaseScript's methods to avoid actual config loading/DB connection
        self.base_patcher = patch(
            "dewey.core.base_script.BaseScript.__init__", return_value=None
        )
        self.setup_logging_patcher = patch(
            "dewey.core.base_script.BaseScript._setup_logging", return_value=None
        )
        self.load_config_patcher = patch(
            "dewey.core.base_script.BaseScript._load_config",
            return_value=self.mock_config,
        )
        self.initialize_db_patcher = patch(
            "dewey.core.base_script.BaseScript._initialize_db_connection",
            return_value=None,
        )
        self.initialize_llm_patcher = patch(
            "dewey.core.base_script.BaseScript._initialize_llm_client",
            return_value=None,
        )

        self.base_mock = self.base_patcher.start()
        self.setup_logging_mock = self.setup_logging_patcher.start()
        self.load_config_mock = self.load_config_patcher.start()
        self.initialize_db_mock = self.initialize_db_patcher.start()
        self.initialize_llm_mock = self.initialize_llm_patcher.start()

        self.cri = CompanyResearchIntegration()
        self.cri.logger = self.mock_logger
        self.cri.db_conn = self.mock_db_conn
        self.cri.llm_client = self.mock_llm_client
        self.cri.config = self.mock_config

    def tearDown(self) -> None:
        """Tear down test environment."""
        self.base_patcher.stop()
        self.setup_logging_patcher.stop()
        self.load_config_patcher.stop()
        self.initialize_db_patcher.stop()
        self.initialize_llm_patcher.stop()

    def test_init(self) -> None:
        """Test the __init__ method."""
        self.base_mock.assert_called_once_with(
            config_section="company_research", requires_db=True, enable_llm=True
        )
        self.setup_logging_mock.assert_called_once()
        self.load_config_mock.assert_called_once()
        self.initialize_db_mock.assert_called_once()
        self.initialize_llm_mock.assert_called_once()
        self.mock_logger.info.assert_called_with(
            "Initialized CompanyResearchIntegration"
        )

    def test_run_success(self) -> None:
        """Test the run method with successful execution."""
        mock_company_data = {"key": "value"}
        mock_processed_data = {"processed_key": "processed_value"}

        self.cri._retrieve_company_data = MagicMock(
            return_value=mock_company_data
        )
        self.cri._process_company_data = MagicMock(
            return_value=mock_processed_data
        )
        self.cri._store_company_data = MagicMock()

        self.cri.run()

        self.cri.logger.info.assert_any_call(
            "Starting company research integration..."
        )
        self.cri.logger.debug.assert_called_with("API Key: test_api_key")
        self.cri._retrieve_company_data.assert_called_once()
        self.cri._process_company_data.assert_called_once_with(
            mock_company_data
        )
        self.cri._store_company_data.assert_called_once_with(
            mock_processed_data
        )
        self.cri.logger.info.assert_any_call(
            "Company research integration completed successfully."
        )

    def test_run_exception(self) -> None:
        """Test the run method with an exception raised."""
        self.cri._retrieve_company_data = MagicMock(
            side_effect=Exception("Test Exception")
        )

        with self.assertRaises(Exception) as context:
            self.cri.run()

        self.cri.logger.info.assert_called_with(
            "Starting company research integration..."
        )
        self.cri.logger.exception.assert_called_once()
        self.assertEqual(str(context.exception), "Test Exception")

    def test_retrieve_company_data_not_implemented(self) -> None:
        """Test _retrieve_company_data raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as context:
            self.cri._retrieve_company_data()

        self.cri.logger.info.assert_called_with("Retrieving company data...")
        self.assertEqual(
            str(context.exception), "Retrieval of company data not implemented."
        )

    def test_process_company_data_not_implemented(self) -> None:
        """Test _process_company_data raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as context:
            self.cri._process_company_data({"some": "data"})

        self.cri.logger.info.assert_called_with("Processing company data...")
        self.assertEqual(
            str(context.exception), "Processing of company data not implemented."
        )

    def test_store_company_data_not_implemented(self) -> None:
        """Test _store_company_data raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as context:
            self.cri._store_company_data({"some": "data"})

        self.cri.logger.info.assert_called_with("Storing company data...")
        self.assertEqual(
            str(context.exception), "Storage of company data not implemented."
        )

    def test_get_config_value(self) -> None:
        """Test the get_config_value method."""
        # Test case 1: Key exists
        value = self.cri.get_config_value("api_key")
        self.assertEqual(value, None)

        # Test case 2: Key does not exist, return default
        value = self.cri.get_config_value("nonexistent_key", "default_value")
        self.assertEqual(value, "default_value")

        # Test case 3: Nested key exists
        self.cri.config = {"section": {"subsection": {"key": "nested_value"}}}
        value = self.cri.get_config_value("section.subsection.key")
        self.assertEqual(value, "nested_value")

        # Test case 4: Nested key does not exist, return default
        value = self.cri.get_config_value(
            "section.nonexistent_subsection.key", "default_value"
        )
        self.assertEqual(value, "default_value")

        # Test case 5: Intermediate key does not exist, return default
        value = self.cri.get_config_value(
            "section.nonexistent_subsection.key", "default_value"
        )
        self.assertEqual(value, "default_value")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args: MagicMock) -> None:
        """Test parse_args updates log level."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        self.cri.parse_args()

        self.assertEqual(self.cri.logger.level, logging.DEBUG)
        self.cri.logger.debug.assert_called_with("Log level set to DEBUG")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config(self, mock_parse_args: MagicMock) -> None:
        """Test parse_args updates config from file."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "test_config.yaml"
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", unittest.mock.mock_open(read_data="test: value")
        ), patch("yaml.safe_load", return_value={"test": "value"}):
            self.cri.parse_args()

        self.assertEqual(self.cri.config, {"test": "value"})
        self.cri.logger.info.assert_called_with(
            "Loaded configuration from test_config.yaml"
        )

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(
        self, mock_parse_args: MagicMock
    ) -> None:
        """Test parse_args exits if config file not found."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "nonexistent_config.yaml"
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch("pathlib.Path.exists", return_value=False), self.assertRaises(
            SystemExit
        ) as context:
            self.cri.parse_args()

        self.assertEqual(context.exception.code, 1)
        self.cri.logger.error.assert_called_with(
            "Configuration file not found: nonexistent_config.yaml"
        )

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_db_connection_string(
        self, mock_parse_args: MagicMock
    ) -> None:
        """Test parse_args updates db connection string."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = "test_db_string"
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch(
            "dewey.core.db.connection.get_connection", return_value="test_conn"
        ):
            self.cri.parse_args()

        self.assertEqual(self.cri.db_conn, "test_conn")
        self.cri.logger.info.assert_called_with("Using custom database connection")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_llm_model(self, mock_parse_args: MagicMock) -> None:
        """Test parse_args updates LLM model."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = "test_llm_model"
        mock_parse_args.return_value = mock_args

        with patch(
            "dewey.llm.llm_utils.get_llm_client", return_value="test_llm_client"
        ):
            self.cri.parse_args()

        self.assertEqual(self.cri.llm_client, "test_llm_client")
        self.cri.logger.info.assert_called_with(
            "Using custom LLM model: test_llm_model"
        )

    def test_cleanup(self) -> None:
        """Test the _cleanup method."""
        self.cri.db_conn = MagicMock()
        self.cri._cleanup()
        self.cri.db_conn.close.assert_called_once()
        self.cri.logger.debug.assert_called_with("Closing database connection")

        self.cri.db_conn.close.side_effect = Exception("Close Error")
        self.cri._cleanup()
        self.cri.logger.warning.assert_called_with(
            "Error closing database connection: Close Error"
        )

    def test_get_path(self) -> None:
        """Test the get_path method."""
        # Test case 1: Absolute path
        absolute_path = "/absolute/path"
        result = self.cri.get_path(absolute_path)
        self.assertEqual(result, Path(absolute_path))

        # Test case 2: Relative path
        relative_path = "relative/path"
        expected_path = self.cri.PROJECT_ROOT / relative_path
        result = self.cri.get_path(relative_path)
        self.assertEqual(result, expected_path)

    @patch("argparse.ArgumentParser.add_argument")
    def test_setup_argparse(self, mock_add_argument: MagicMock) -> None:
        """Test the setup_argparse method."""
        parser = self.cri.setup_argparse()
        self.assertIsNotNone(parser)
        self.assertEqual(mock_add_argument.call_count, 4)

        # Verify specific calls to add_argument
        expected_calls = [
            unittest.mock.call(
                "--config",
                help=f"Path to configuration file (default: {self.cri.CONFIG_PATH})",
            ),
            unittest.mock.call(
                "--log-level",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                help="Set logging level",
            ),
            unittest.mock.call(
                "--db-connection-string",
                help="Database connection string (overrides config)",
            ),
            unittest.mock.call(
                "--llm-model", help="LLM model to use (overrides config)"
            ),
        ]
        mock_add_argument.assert_has_calls(expected_calls, any_order=True)

    @patch.object(CompanyResearchIntegration, "parse_args")
    @patch.object(CompanyResearchIntegration, "run")
    def test_execute_success(self, mock_run: MagicMock, mock_parse_args: MagicMock) -> None:
        """Test execute method for successful execution."""
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args

        self.cri.execute()

        mock_parse_args.assert_called_once()
        self.cri.logger.info.assert_any_call(
            f"Starting execution of {self.cri.name}"
        )
        mock_run.assert_called_once()
        self.cri.logger.info.assert_any_call(
            f"Completed execution of {self.cri.name}"
        )

    @patch.object(CompanyResearchIntegration, "parse_args")
    @patch.object(CompanyResearchIntegration, "run")
    def test_execute_keyboard_interrupt(self, mock_run: MagicMock, mock_parse_args: MagicMock) -> None:
        """Test execute method handles KeyboardInterrupt."""
        mock_parse_args.return_value = MagicMock()
        mock_run.side_effect = KeyboardInterrupt

        with self.assertRaises(SystemExit) as context:
            self.cri.execute()

        self.assertEqual(context.exception.code, 1)
        self.cri.logger.warning.assert_called_with("Script interrupted by user")

    @patch.object(CompanyResearchIntegration, "parse_args")
    @patch.object(CompanyResearchIntegration, "run")
    def test_execute_exception(self, mock_run: MagicMock, mock_parse_args: MagicMock) -> None:
        """Test execute method handles exceptions during execution."""
        mock_parse_args.return_value = MagicMock()
        mock_run.side_effect = ValueError("Test error")

        with self.assertRaises(SystemExit) as context:
            self.cri.execute()

        self.assertEqual(context.exception.code, 1)
        self.cri.logger.error.assert_called_once()

