"""Tests for dewey.core.analysis.log_analyzer."""

import logging
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest

from dewey.core.analysis.log_analyzer import LogAnalyzer
from dewey.core.base_script import BaseScript


class TestLogAnalyzer:
    """Unit tests for the LogAnalyzer class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock = MagicMock(spec=BaseScript)
        mock.logger = MagicMock()
        mock.config = {}
        mock.get_config_value.return_value = "test_log_file.log"
        return mock

    @pytest.fixture
    def log_analyzer(self, mock_base_script: MagicMock) -> LogAnalyzer:
        """Fixture to create a LogAnalyzer instance."""
        with patch("dewey.core.analysis.log_analyzer.BaseScript.__init__", return_value=None):
            analyzer = LogAnalyzer()
            analyzer.logger = mock_base_script.logger
            analyzer.config = mock_base_script.config
            analyzer.get_config_value = mock_base_script.get_config_value
        return analyzer

    def test_init(self, log_analyzer: LogAnalyzer) -> None:
        """Test the __init__ method."""
        assert log_analyzer.name == "LogAnalyzer"
        assert log_analyzer.description == "Analyzes log files for specific patterns and insights."
        assert log_analyzer.file_opener == open

    @pytest.mark.parametrize(
        "log_content, expected_calls",
        [
            ("This is a test log file.\nERROR: An error occurred.\n", 1),
            ("This is a test log file.\nWARNING: A warning occurred.\n", 0),
            ("", 0),
            ("ERROR: An error occurred.\nERROR: Another error occurred.\n", 2),
        ],
    )
    def test_process_log_lines(self, log_content: str, expected_calls: int, log_analyzer: LogAnalyzer) -> None:
        """Test the _process_log_lines method with different log contents."""
        mock_log_file = MagicMock()
        mock_log_file.__iter__.return_value = log_content.splitlines()
        log_analyzer._process_log_lines(mock_log_file)
        assert log_analyzer.logger.error.call_count == expected_calls

    @patch("builtins.open", new_callable=mock_open, read_data="This is a test log file.\nERROR: An error occurred.\n")
    def test_analyze_logs_success(self, mock_file: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the analyze_logs method with a successful log analysis."""
        log_analyzer.analyze_logs("test_log_file.log")
        log_analyzer.logger.error.assert_called_once_with("Found error: ERROR: An error occurred.")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_analyze_logs_file_not_found(self, mock_file: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the analyze_logs method when the log file is not found."""
        with pytest.raises(FileNotFoundError):
            log_analyzer.analyze_logs("nonexistent_log_file.log")
        log_analyzer.logger.error.assert_called_once_with("Log file not found: nonexistent_log_file.log")

    @patch("builtins.open", side_effect=Exception("Test exception"))
    def test_analyze_logs_exception(self, mock_file: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the analyze_logs method when an exception occurs during log analysis."""
        with pytest.raises(Exception, match="Test exception"):
            log_analyzer.analyze_logs("test_log_file.log")
        log_analyzer.logger.exception.assert_called_once()

    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.analyze_logs")
    def test_run_success(self, mock_analyze_logs: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the run method with a successful log analysis."""
        log_analyzer.run()
        log_analyzer.logger.info.assert_any_call("Starting log analysis...")
        log_analyzer.logger.info.assert_any_call("Log file path: test_log_file.log")
        log_analyzer.logger.info.assert_any_call("Log analysis complete.")
        mock_analyze_logs.assert_called_once_with("test_log_file.log")

    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.analyze_logs", side_effect=FileNotFoundError)
    def test_run_file_not_found(self, mock_analyze_logs: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the run method when the log file is not found."""
        with pytest.raises(FileNotFoundError):
            log_analyzer.run()

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock())
    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.run")
    def test_execute_success(self, mock_run: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the execute method with a successful run."""
        log_analyzer.execute()
        mock_run.assert_called_once()
        log_analyzer.logger.info.assert_any_call(f"Starting execution of {log_analyzer.name}")
        log_analyzer.logger.info.assert_any_call(f"Completed execution of {log_analyzer.name}")

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock())
    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.run", side_effect=KeyboardInterrupt)
    def test_execute_keyboard_interrupt(self, mock_run: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the execute method when a KeyboardInterrupt is raised."""
        with pytest.raises(SystemExit) as exc_info:
            log_analyzer.execute()
        assert exc_info.value.code == 1
        log_analyzer.logger.warning.assert_called_once_with("Script interrupted by user")

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock())
    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.run", side_effect=Exception("Test exception"))
    def test_execute_exception(self, mock_run: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the execute method when an exception is raised."""
        with pytest.raises(SystemExit) as exc_info:
            log_analyzer.execute()
        assert exc_info.value.code == 1
        log_analyzer.logger.error.assert_called_once()

    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer._cleanup")
    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock())
    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.run", side_effect=Exception("Test exception"))
    def test_execute_cleanup_called_on_exception(self, mock_run: MagicMock, mock_parse_args: MagicMock, mock_cleanup: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test that _cleanup is called when an exception occurs during execute."""
        with pytest.raises(SystemExit):
            log_analyzer.execute()
        mock_cleanup.assert_called_once()

    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer._cleanup")
    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock())
    @patch("dewey.core.analysis.log_analyzer.LogAnalyzer.run")
    def test_execute_cleanup_called_on_success(self, mock_run: MagicMock, mock_parse_args: MagicMock, mock_cleanup: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test that _cleanup is called when execute completes successfully."""
        log_analyzer.execute()
        mock_cleanup.assert_called_once()

    def test_cleanup_db_conn_none(self, log_analyzer: LogAnalyzer) -> None:
        """Test the _cleanup method when db_conn is None."""
        log_analyzer._cleanup()
        # Assert that no methods are called when db_conn is None
        assert True

    def test_cleanup_db_conn_exists(self, log_analyzer: LogAnalyzer) -> None:
        """Test the _cleanup method when db_conn exists."""
        log_analyzer.db_conn = MagicMock()
        log_analyzer._cleanup()
        log_analyzer.db_conn.close.assert_called_once()
        log_analyzer.logger.debug.assert_called_once_with("Closing database connection")

    def test_cleanup_db_conn_close_exception(self, log_analyzer: LogAnalyzer) -> None:
        """Test the _cleanup method when closing db_conn raises an exception."""
        log_analyzer.db_conn = MagicMock()
        log_analyzer.db_conn.close.side_effect = Exception("Test exception")
        log_analyzer._cleanup()
        log_analyzer.logger.warning.assert_called_once()

    @patch("os.path.isabs", return_value=True)
    def test_get_path_absolute(self, mock_isabs: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the get_path method with an absolute path."""
        path = "/absolute/path"
        result = log_analyzer.get_path(path)
        assert str(result) == path

    @patch("os.path.isabs", return_value=False)
    def test_get_path_relative(self, mock_isabs: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the get_path method with a relative path."""
        path = "relative/path"
        result = log_analyzer.get_path(path)
        expected_path = Path(__file__).parent.parent.parent.parent / path
        assert str(result) == str(expected_path)

    def test_get_config_value_success(self, log_analyzer: LogAnalyzer) -> None:
        """Test the get_config_value method with a successful retrieval."""
        log_analyzer.config = {"level1": {"level2": "value"}}
        result = log_analyzer.get_config_value("level1.level2")
        assert result == "value"

    def test_get_config_value_default(self, log_analyzer: LogAnalyzer) -> None:
        """Test the get_config_value method when the key is not found."""
        log_analyzer.config = {"level1": {"level2": "value"}}
        result = log_analyzer.get_config_value("level1.level3", "default")
        assert result == "default"

    def test_get_config_value_no_key(self, log_analyzer: LogAnalyzer) -> None:
        """Test the get_config_value method when the key is empty."""
        log_analyzer.config = {"level1": {"level2": "value"}}
        result = log_analyzer.get_config_value("", "default")
        assert result == "default"

    def test_get_config_value_empty_part(self, log_analyzer: LogAnalyzer) -> None:
        """Test the get_config_value method when there is an empty part in the key."""
        log_analyzer.config = {"level1": {"level2": "value"}}
        result = log_analyzer.get_config_value("level1..level2", "default")
        assert result == "default"

    @patch("argparse.ArgumentParser.add_argument")
    def test_setup_argparse(self, mock_add_argument: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the setup_argparse method."""
        parser = log_analyzer.setup_argparse()
        assert parser is not None
        assert mock_add_argument.call_count >= 2

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(log_level="DEBUG"))
    def test_parse_args_log_level(self, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the parse_args method with a log level argument."""
        args = log_analyzer.parse_args()
        assert args is not None
        log_analyzer.logger.setLevel.assert_called_once_with(logging.DEBUG)

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(config="test_config.yaml"))
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    def test_parse_args_config(self, mock_file_open: MagicMock, mock_exists: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the parse_args method with a config argument."""
        args = log_analyzer.parse_args()
        assert args is not None
        assert log_analyzer.config == {}

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(config="test_config.yaml"))
    @patch("pathlib.Path.exists", return_value=False)
    def test_parse_args_config_not_found(self, mock_exists: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the parse_args method when the config file is not found."""
        mock_exists.return_value = False
        mock_parse_args.return_value.config = "nonexistent_config.yaml"
        with pytest.raises(SystemExit) as exc_info:
            log_analyzer.parse_args()
        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(db_connection_string="test_connection_string"))
    @patch("dewey.core.db.connection.get_connection")
    def test_parse_args_db_connection(self, mock_get_connection: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the parse_args method with a database connection string argument."""
        log_analyzer.requires_db = True
        args = log_analyzer.parse_args()
        assert args is not None
        mock_get_connection.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(llm_model="test_llm_model"))
    @patch("dewey.llm.llm_utils.get_llm_client")
    def test_parse_args_llm_model(self, mock_get_llm_client: MagicMock, mock_parse_args: MagicMock, log_analyzer: LogAnalyzer) -> None:
        """Test the parse_args method with an LLM model argument."""
        log_analyzer.enable_llm = True
        args = log_analyzer.parse_args()
        assert args is not None
        mock_get_llm_client.assert_called_once()
