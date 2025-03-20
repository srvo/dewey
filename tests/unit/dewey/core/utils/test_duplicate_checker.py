import unittest
from unittest.mock import patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.utils.duplicate_checker import DuplicateChecker


class TestDuplicateChecker(unittest.TestCase):
    """Unit tests for the DuplicateChecker class."""

    def setUp(self):
        """Setup method to create a DuplicateChecker instance before each test."""
        self.duplicate_checker = DuplicateChecker()

    def test_inheritance(self):
        """Test that DuplicateChecker inherits from BaseScript."""
        self.assertTrue(issubclass(DuplicateChecker, BaseScript))

    def test_init(self):
        """Test the __init__ method."""
        self.assertIsInstance(self.duplicate_checker, DuplicateChecker)
        self.assertEqual(self.duplicate_checker.config_section, "duplicate_checker")

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.get_config_value")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_run_success(self, mock_logger, mock_get_config_value):
        """Test the run method with successful execution."""
        mock_get_config_value.return_value = 0.9
        self.duplicate_checker.run()
        mock_logger.info.assert_called_with("Duplicate check complete.")
        mock_logger.debug.assert_called_with("Similarity threshold: 0.9")

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.get_config_value")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_run_exception(self, mock_logger, mock_get_config_value):
        """Test the run method when an exception occurs."""
        mock_get_config_value.side_effect = Exception("Test exception")
        with self.assertRaises(Exception) as context:
            self.duplicate_checker.run()
        self.assertEqual(str(context.exception), "Test exception")
        mock_logger.error.assert_called_once()

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.execute")
    def test_main_execution(self, mock_execute):
        """Test that the execute method is called when the script is run as main."""
        with patch("dewey.core.utils.duplicate_checker.__name__", "__main__"):
            import dewey.core.utils.duplicate_checker

            dewey.core.utils.duplicate_checker.DuplicateChecker().execute()
            mock_execute.assert_called_once()

    def test_get_config_value_existing_key(self):
        """Test get_config_value method with an existing key."""
        self.duplicate_checker.config = {"duplicate_checker": {"similarity_threshold": 0.75}}
        value = self.duplicate_checker.get_config_value("duplicate_checker.similarity_threshold")
        self.assertEqual(value, 0.75)

    def test_get_config_value_nonexistent_key(self):
        """Test get_config_value method with a nonexistent key."""
        self.duplicate_checker.config = {"duplicate_checker": {"similarity_threshold": 0.75}}
        value = self.duplicate_checker.get_config_value("duplicate_checker.nonexistent_key", "default_value")
        self.assertEqual(value, "default_value")

    def test_get_config_value_nested_key(self):
        """Test get_config_value method with a nested key."""
        self.duplicate_checker.config = {"duplicate_checker": {"nested": {"key": "nested_value"}}}
        value = self.duplicate_checker.get_config_value("duplicate_checker.nested.key")
        self.assertEqual(value, "nested_value")

    def test_get_config_value_default_value(self):
        """Test get_config_value method with a default value."""
        self.duplicate_checker.config = {}
        value = self.duplicate_checker.get_config_value("nonexistent_key", "default_value")
        self.assertEqual(value, "default_value")

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_execute_keyboard_interrupt(self, mock_logger):
        """Test the execute method when a KeyboardInterrupt occurs."""
        with patch("dewey.core.utils.duplicate_checker.DuplicateChecker.parse_args", side_effect=KeyboardInterrupt):
            with self.assertRaises(SystemExit) as context:
                self.duplicate_checker.execute()
            self.assertEqual(context.exception.code, 1)
            mock_logger.warning.assert_called_with("Script interrupted by user")

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_execute_exception(self, mock_logger):
        """Test the execute method when an exception occurs."""
        with patch("dewey.core.utils.duplicate_checker.DuplicateChecker.parse_args", side_effect=Exception("Test exception")):
            with self.assertRaises(SystemExit) as context:
                self.duplicate_checker.execute()
            self.assertEqual(context.exception.code, 1)
            mock_logger.error.assert_called_once()

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker._cleanup")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.run")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.parse_args")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_execute_success(self, mock_logger, mock_parse_args, mock_run, mock_cleanup):
        """Test the execute method with successful execution."""
        mock_parse_args.return_value = None
        self.duplicate_checker.execute()
        mock_logger.info.assert_called()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_cleanup_db_connection_error(self, mock_logger):
        """Test the _cleanup method when closing the database connection raises an exception."""
        self.duplicate_checker.db_conn = unittest.mock.Mock()
        self.duplicate_checker.db_conn.close.side_effect = Exception("Test exception")
        self.duplicate_checker._cleanup()
        mock_logger.warning.assert_called_once()

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.logger")
    def test_cleanup_db_connection_success(self, mock_logger):
        """Test the _cleanup method when the database connection is closed successfully."""
        self.duplicate_checker.db_conn = unittest.mock.Mock()
        self.duplicate_checker._cleanup()
        self.duplicate_checker.db_conn.close.assert_called_once()
        mock_logger.debug.assert_called_with("Closing database connection")

    def test_get_path_absolute(self):
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path"
        path = self.duplicate_checker.get_path(absolute_path)
        self.assertEqual(str(path), absolute_path)

    def test_get_path_relative(self):
        """Test get_path method with a relative path."""
        relative_path = "relative/path"
        expected_path = self.duplicate_checker.PROJECT_ROOT / relative_path
        path = self.duplicate_checker.get_path(relative_path)
        self.assertEqual(path, expected_path)

    def test_setup_logging_default_config(self):
        """Test setup_logging method with default configuration."""
        with patch("dewey.core.utils.duplicate_checker.open", side_effect=FileNotFoundError):
            self.duplicate_checker._setup_logging()
            self.assertEqual(self.duplicate_checker.logger.level, logging.INFO)

    def test_setup_logging_custom_config(self):
        """Test setup_logging method with custom configuration."""
        config_data = {
            "core": {
                "logging": {
                    "level": "DEBUG",
                    "format": "%(levelname)s - %(message)s",
                    "date_format": "%Y-%m-%d",
                }
            }
        }
        with patch("dewey.core.utils.duplicate_checker.open", unittest.mock.mock_open(read_data=yaml.dump(config_data))):
            self.duplicate_checker._setup_logging()
            self.assertEqual(self.duplicate_checker.logger.level, logging.DEBUG)

    @patch("dewey.core.utils.duplicate_checker.yaml.safe_load")
    @patch("dewey.core.utils.duplicate_checker.open", new_callable=unittest.mock.mock_open)
    def test_load_config_success(self, mock_open, mock_safe_load):
        """Test _load_config method with successful loading."""
        mock_safe_load.return_value = {"test_key": "test_value"}
        config = self.duplicate_checker._load_config()
        self.assertEqual(config, {"test_key": "test_value"})
        mock_open.assert_called_with(self.duplicate_checker.CONFIG_PATH, 'r')

    @patch("dewey.core.utils.duplicate_checker.open", side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_open):
        """Test _load_config method when the configuration file is not found."""
        with self.assertRaises(FileNotFoundError):
            self.duplicate_checker._load_config()

    @patch("dewey.core.utils.duplicate_checker.yaml.safe_load", side_effect=yaml.YAMLError)
    @patch("dewey.core.utils.duplicate_checker.open", new_callable=unittest.mock.mock_open)
    def test_load_config_yaml_error(self, mock_open, mock_safe_load):
        """Test _load_config method when there is a YAML error."""
        with self.assertRaises(yaml.YAMLError):
            self.duplicate_checker._load_config()

    @patch("dewey.core.utils.duplicate_checker.get_connection")
    def test_initialize_db_connection_success(self, mock_get_connection):
        """Test _initialize_db_connection method with successful connection."""
        self.duplicate_checker.config = {"core": {"database": {"test_key": "test_value"}}}
        self.duplicate_checker._initialize_db_connection()
        mock_get_connection.assert_called_with({"test_key": "test_value"})
        self.assertIsNotNone(self.duplicate_checker.db_conn)

    @patch("dewey.core.utils.duplicate_checker.get_connection", side_effect=Exception("Test exception"))
    def test_initialize_db_connection_exception(self, mock_get_connection):
        """Test _initialize_db_connection method when an exception occurs."""
        self.duplicate_checker.config = {"core": {"database": {"test_key": "test_value"}}}
        with self.assertRaises(Exception) as context:
            self.duplicate_checker._initialize_db_connection()
        self.assertEqual(str(context.exception), "Test exception")

    @patch("dewey.core.utils.duplicate_checker.get_llm_client")
    def test_initialize_llm_client_success(self, mock_get_llm_client):
        """Test _initialize_llm_client method with successful initialization."""
        self.duplicate_checker.config = {"llm": {"test_key": "test_value"}}
        self.duplicate_checker._initialize_llm_client()
        mock_get_llm_client.assert_called_with({"test_key": "test_value"})
        self.assertIsNotNone(self.duplicate_checker.llm_client)

    @patch("dewey.core.utils.duplicate_checker.get_llm_client", side_effect=Exception("Test exception"))
    def test_initialize_llm_client_exception(self, mock_get_llm_client):
        """Test _initialize_llm_client method when an exception occurs."""
        self.duplicate_checker.config = {"llm": {"test_key": "test_value"}}
        with self.assertRaises(Exception) as context:
            self.duplicate_checker._initialize_llm_client()
        self.assertEqual(str(context.exception), "Test exception")

    def test_setup_argparse(self):
        """Test setup_argparse method."""
        parser = self.duplicate_checker.setup_argparse()
        self.assertIsNotNone(parser)

    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.setup_argparse")
    def test_parse_args(self, mock_setup_argparse):
        """Test parse_args method."""
        mock_parser = unittest.mock.Mock()
        mock_setup_argparse.return_value = mock_parser
        mock_parser.parse_args.return_value = unittest.mock.Mock()
        args = self.duplicate_checker.parse_args()
        self.assertIsNotNone(args)

    @patch("dewey.core.utils.duplicate_checker.logging")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.setup_argparse")
    def test_parse_args_log_level(self, mock_setup_argparse, mock_logging):
        """Test parse_args method with log level argument."""
        mock_parser = unittest.mock.Mock()
        mock_setup_argparse.return_value = mock_parser
        mock_args = unittest.mock.Mock()
        mock_args.log_level = "DEBUG"
        mock_parser.parse_args.return_value = mock_args
        self.duplicate_checker.parse_args()
        self.duplicate_checker.logger.setLevel.assert_called_with(mock_logging.DEBUG)

    @patch("dewey.core.utils.duplicate_checker.logging")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.setup_argparse")
    def test_parse_args_config(self, mock_setup_argparse, mock_logging):
        """Test parse_args method with config argument."""
        mock_parser = unittest.mock.Mock()
        mock_setup_argparse.return_value = mock_parser
        mock_args = unittest.mock.Mock()
        mock_args.config = "test_config.yaml"
        mock_parser.parse_args.return_value = mock_args
        with patch("dewey.core.utils.duplicate_checker.open", unittest.mock.mock_open(read_data="test: test")):
            self.duplicate_checker.parse_args()
            self.assertEqual(self.duplicate_checker.config, {"test": "test"})

    @patch("dewey.core.utils.duplicate_checker.logging")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.setup_argparse")
    def test_parse_args_db_connection_string(self, mock_setup_argparse, mock_logging):
        """Test parse_args method with db_connection_string argument."""
        mock_parser = unittest.mock.Mock()
        mock_setup_argparse.return_value = mock_parser
        mock_args = unittest.mock.Mock()
        mock_args.db_connection_string = "test_connection_string"
        mock_parser.parse_args.return_value = mock_args
        self.duplicate_checker.requires_db = True
        with patch("dewey.core.utils.duplicate_checker.get_connection") as mock_get_connection:
            self.duplicate_checker.parse_args()
            mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})

    @patch("dewey.core.utils.duplicate_checker.logging")
    @patch("dewey.core.utils.duplicate_checker.DuplicateChecker.setup_argparse")
    def test_parse_args_llm_model(self, mock_setup_argparse, mock_logging):
        """Test parse_args method with llm_model argument."""
        mock_parser = unittest.mock.Mock()
        mock_setup_argparse.return_value = mock_parser
        mock_args = unittest.mock.Mock()
        mock_args.llm_model = "test_llm_model"
        mock_parser.parse_args.return_value = mock_args
        self.duplicate_checker.enable_llm = True
        with patch("dewey.core.utils.duplicate_checker.get_llm_client") as mock_get_llm_client:
            self.duplicate_checker.parse_args()
            mock_get_llm_client.assert_called_with({"model": "test_llm_model"})

