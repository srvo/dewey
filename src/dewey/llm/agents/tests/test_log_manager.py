import unittest
from unittest.mock import patch
from typing import Any

from dewey.core.base_script import BaseScript
from dewey.core.utils.log_manager import LogManager


class TestLogManager(unittest.TestCase):
    """Tests for the LogManager class."""

    @patch.object(BaseScript, 'get_config_value')
    @patch.object(BaseScript, 'logger')
    def test_run(self, mock_logger, mock_get_config_value):
        """Test that the run method logs a message."""
        log_manager = LogManager()
        log_manager.run()
        mock_logger.info.assert_called_once_with("LogManager is running.")

    @patch.object(BaseScript, 'get_config_value')
    def test_get_log_level(self, mock_get_config_value):
        """Test that the get_log_level method returns the log level from config."""
        mock_get_config_value.return_value = "DEBUG"
        log_manager = LogManager()
        log_level = log_manager.get_log_level()
        self.assertEqual(log_level, "DEBUG")
        mock_get_config_value.assert_called_once_with("log_level", default="INFO")

    @patch.object(BaseScript, 'get_config_value')
    def test_get_log_file_path(self, mock_get_config_value):
        """Test that the get_log_file_path method returns the log file path from config."""
        mock_get_config_value.return_value = "/path/to/log/file.log"
        log_manager = LogManager()
        log_file_path = log_manager.get_log_file_path()
        self.assertEqual(log_file_path, "/path/to/log/file.log")
        mock_get_config_value.assert_called_once_with("log_file_path", default="application.log")

    @patch.object(BaseScript, 'get_config_value')
    @patch.object(BaseScript, 'logger')
    def test_some_other_function(self, mock_logger, mock_get_config_value):
        """Test the some_other_function method."""
        mock_get_config_value.return_value = "test_value"
        log_manager = LogManager()
        log_manager.some_other_function("test_arg")
        mock_get_config_value.assert_called_once_with("some_config_key", default="default_value")
        mock_logger.info.assert_called_once_with("Some value: test_value, Arg: test_arg")


if __name__ == "__main__":
    unittest.main()
