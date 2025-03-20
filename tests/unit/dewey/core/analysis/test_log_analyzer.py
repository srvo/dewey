import logging
import unittest.mock
from pathlib import Path
from typing import Any, Dict
import pytest

from dewey.core.analysis.log_analyzer import LogAnalyzer
from dewey.core.base_script import BaseScript


class TestLogAnalyzer:
    """Unit tests for the LogAnalyzer class."""

    @pytest.fixture
    def log_analyzer(self, tmp_path: Path) -> LogAnalyzer:
        """Fixture to create a LogAnalyzer instance with a temporary config."""
        config_data = {
            "log_analyzer": {
                "log_file_path": str(tmp_path / "test.log")
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
            }
        }
        with open(tmp_path / "config.yaml", "w") as f:
            import yaml
            yaml.dump(config_data, f)

        with unittest.mock.patch("dewey.core.base_script.CONFIG_PATH", tmp_path / "config.yaml"):
            analyzer = LogAnalyzer()
        return analyzer

    def test_init(self, log_analyzer: LogAnalyzer) -> None:
        """Test the __init__ method."""
        assert log_analyzer.script_name == "LogAnalyzer"
        assert isinstance(log_analyzer, BaseScript)
        assert isinstance(log_analyzer.logger, logging.Logger)

    def test_run_success(self, log_analyzer: LogAnalyzer, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with a successful log analysis."""
        log_file_path = tmp_path / "test.log"
        log_file_path.write_text("This is a test log file.\nERROR: An error occurred.\n")
        caplog.set_level(logging.INFO)
        log_analyzer.run()
        assert "Starting log analysis..." in caplog.text
        assert f"Log file path: {log_file_path}" in caplog.text
        assert "Log analysis complete." in caplog.text
        assert "Found error: ERROR: An error occurred." in caplog.text

    def test_run_file_not_found(self, log_analyzer: LogAnalyzer, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when the log file is not found."""
        caplog.set_level(logging.ERROR)
        with pytest.raises(FileNotFoundError):
            log_analyzer.run()
        assert "Log file not found:" in caplog.text

    def test_analyze_logs_success(self, log_analyzer: LogAnalyzer, tmp_path: Path) -> None:
        """Test the analyze_logs method with a successful log analysis."""
        log_file_path = tmp_path / "test.log"
        log_file_path.write_text("This is a test log file.\nERROR: An error occurred.\n")
        with unittest.mock.patch.object(log_analyzer.logger, "error") as mock_error:
            log_analyzer.analyze_logs(str(log_file_path))
            mock_error.assert_called_once()
            assert "ERROR: An error occurred." in str(mock_error.call_args)

    def test_analyze_logs_file_not_found(self, log_analyzer: LogAnalyzer, tmp_path: Path) -> None:
        """Test the analyze_logs method when the log file is not found."""
        log_file_path = tmp_path / "nonexistent.log"
        with pytest.raises(FileNotFoundError):
            log_analyzer.analyze_logs(str(log_file_path))

    def test_analyze_logs_exception(self, log_analyzer: LogAnalyzer, tmp_path: Path) -> None:
        """Test the analyze_logs method when an exception occurs during log analysis."""
        log_file_path = tmp_path / "test.log"
        log_file_path.write_text("This is a test log file.")
        with open(log_file_path, "w") as f:
            f.write("test")
        with unittest.mock.patch("builtins.open", side_effect=Exception("Test exception")):
            with pytest.raises(Exception, match="Test exception"):
                log_analyzer.analyze_logs(str(log_file_path))

    def test_get_config_value(self, log_analyzer: LogAnalyzer) -> None:
        """Test the get_config_value method."""
        log_file_path = log_analyzer.get_config_value("log_analyzer.log_file_path")
        assert log_file_path is not None

        default_value = log_analyzer.get_config_value("nonexistent_key", "default")
        assert default_value == "default"
