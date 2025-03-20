"""Tests for dewey.core.analysis."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import logging
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

from dewey.core.analysis import AnalysisScript
from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import generate


class TestAnalysisScript:
    """
    Unit tests for the AnalysisScript class.
    """

    @pytest.fixture
    def analysis_script(self, mock_base_script: MagicMock) -> AnalysisScript:
        """
        Fixture to create an AnalysisScript object.
        """
        with patch("dewey.core.analysis.BaseScript.__init__", return_value=None):
            analysis_script = AnalysisScript()
            analysis_script.name = "TestScript"
            analysis_script.description = "A test script"
            analysis_script.config_section = "test_config"
            analysis_script.requires_db = False
            analysis_script.enable_llm = False
            analysis_script.config = {}
            analysis_script.db_conn = None
            analysis_script.llm_client = None
            analysis_script.logger = MagicMock()
            return analysis_script

    def test_analysis_script_initialization(self, analysis_script: AnalysisScript) -> None:
        """
        Test that the AnalysisScript is initialized correctly.
        """
        assert analysis_script.name == "TestScript"
        assert analysis_script.description == "A test script"
        assert analysis_script.config_section == "test_config"
        assert analysis_script.requires_db is False
        assert analysis_script.enable_llm is False
        assert analysis_script.config == {}
        assert analysis_script.db_conn is None
        assert analysis_script.llm_client is None

    def test_analysis_script_initialization_with_params(self) -> None:
        """
        Test that the AnalysisScript is initialized correctly with parameters.
        """
        with patch("dewey.core.analysis.BaseScript.__init__", return_value=None):
            analysis_script = AnalysisScript(
                name="CustomScript",
                description="A custom script",
                config_section="custom_config",
                requires_db=True,
                enable_llm=True,
            )
            analysis_script.logger = MagicMock()

        assert analysis_script.name == "CustomScript"
        assert analysis_script.description == "A custom script"
        assert analysis_script.config_section == "custom_config"
        assert analysis_script.requires_db is True
        assert analysis_script.enable_llm is True

    def test_run_method_raises_not_implemented_error(self, analysis_script: AnalysisScript) -> None:
        """
        Test that the run method raises a NotImplementedError.
        """
        with pytest.raises(NotImplementedError):
            analysis_script.run()

    def test_execute_method_calls_run(self, analysis_script: AnalysisScript) -> None:
        """
        Test that the execute method calls the run method.
        """
        with patch.object(analysis_script, "parse_args") as mock_parse_args, \
                patch.object(analysis_script, "run") as mock_run:
            mock_parse_args.return_value = argparse.Namespace()
            analysis_script.execute()
            mock_run.assert_called_once()

    def test_execute_method_handles_keyboard_interrupt(self, analysis_script: AnalysisScript, capsys: pytest.CaptureFixture) -> None:
        """
        Test that the execute method handles KeyboardInterrupt.
        """
        with patch.object(analysis_script, "parse_args") as mock_parse_args, \
                patch.object(analysis_script, "run", side_effect=KeyboardInterrupt):
            mock_parse_args.return_value = argparse.Namespace()
            with pytest.raises(SystemExit) as exc_info:
                analysis_script.execute()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Script interrupted by user" in captured.out

    def test_execute_method_handles_exception(self, analysis_script: AnalysisScript, capsys: pytest.CaptureFixture) -> None:
        """
        Test that the execute method handles exceptions.
        """
        with patch.object(analysis_script, "parse_args") as mock_parse_args, \
                patch.object(analysis_script, "run", side_effect=ValueError("Test error")):
            mock_parse_args.return_value = argparse.Namespace()
            with pytest.raises(SystemExit) as exc_info:
                analysis_script.execute()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error executing script: Test error" in captured.out

    def test_cleanup_method_closes_db_connection(self, analysis_script: AnalysisScript) -> None:
        """
        Test that the cleanup method closes the database connection.
        """
        mock_db_conn = MagicMock(spec=DatabaseConnection)
        analysis_script.db_conn = mock_db_conn
        analysis_script._cleanup()
        mock_db_conn.close.assert_called_once()

    def test_cleanup_method_handles_db_connection_error(self, analysis_script: AnalysisScript, caplog: pytest.LogCaptureFixture) -> None:
        """
        Test that the cleanup method handles errors when closing the database connection.
        """
        mock_db_conn = MagicMock(spec=DatabaseConnection)
        mock_db_conn.close.side_effect = ValueError("Test error")
        analysis_script.db_conn = mock_db_conn
        with caplog.at_level(logging.WARNING):
            analysis_script._cleanup()
        assert "Error closing database connection: Test error" in caplog.text

    def test_get_path_method_returns_absolute_path(self, analysis_script: AnalysisScript) -> None:
        """
        Test that the get_path method returns an absolute path when given an absolute path.
        """
        absolute_path = "/absolute/path"
        result = analysis_script.get_path(absolute_path)
        assert result == Path(absolute_path)

    def test_get_path_method_returns_relative_path(self, analysis_script: AnalysisScript) -> None:
        """
        Test that the get_path method returns a path relative to the project root when given a relative path.
        """
        relative_path = "relative/path"
        expected_path = analysis_script.PROJECT_ROOT / relative_path
        result = analysis_script.get_path(relative_path)
        assert result == expected_path

    def test_get_config_value_returns_value_if_exists(self, analysis_script: AnalysisScript, mock_config: Dict[str, Any]) -> None:
        """
        Test that the get_config_value method returns the correct value if the key exists.
        """
        analysis_script.config = mock_config
        result = analysis_script.get_config_value("section.key")
        assert result == "value"

    def test_get_config_value_returns_default_if_key_does_not_exist(self, analysis_script: AnalysisScript, mock_config: Dict[str, Any]) -> None:
        """
        Test that the get_config_value method returns the default value if the key does not exist.
        """
        analysis_script.config = mock_config
        result = analysis_script.get_config_value("section.missing_key", "default_value")
        assert result == "default_value"

    def test_get_config_value_returns_none_if_key_does_not_exist_and_no_default(self, analysis_script: AnalysisScript, mock_config: Dict[str, Any]) -> None:
        """
        Test that the get_config_value method returns None if the key does not exist and no default value is provided.
        """
        analysis_script.config = mock_config
        result = analysis_script.get_config_value("section.missing_key")
        assert result is None

    def test_get_config_value_handles_missing_intermediate_section(self, analysis_script: AnalysisScript, mock_config: Dict[str, Any]) -> None:
        """
        Test that the get_config_value method handles missing intermediate sections in the key path.
        """
        analysis_script.config = mock_config
        result = analysis_script.get_config_value("missing_section.missing_key", "default_value")
        assert result == "default_value"

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_updates_log_level(self, mock_parse_args: MagicMock, analysis_script: AnalysisScript, caplog: pytest.LogCaptureFixture) -> None:
        """
        Test that parse_args updates the log level if specified in the arguments.
        """
        mock_parse_args.return_value = argparse.Namespace(log_level="DEBUG", config=None, db_connection_string=None, llm_model=None)
        with caplog.at_level(logging.DEBUG):
            analysis_script.parse_args()
            assert analysis_script.logger.level == logging.DEBUG
            assert "Log level set to DEBUG" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_updates_config_from_file(self, mock_parse_args: MagicMock, analysis_script: AnalysisScript, tmp_path: Path) -> None:
        """
        Test that parse_args updates the config from a file if specified in the arguments.
        """
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_parse_args.return_value = argparse.Namespace(log_level=None, config=str(config_file), db_connection_string=None, llm_model=None)
        analysis_script.parse_args()
        assert analysis_script.config == config_data

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_handles_missing_config_file(self, mock_parse_args: MagicMock, analysis_script: AnalysisScript, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """
        Test that parse_args handles a missing config file.
        """
        config_file = tmp_path / "missing_config.yaml"
        mock_parse_args.return_value = argparse.Namespace(log_level=None, config=str(config_file), db_connection_string=None, llm_model=None)
        with pytest.raises(SystemExit) as exc_info:
            analysis_script.parse_args()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert f"Configuration file not found: {config_file}" in captured.out

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.analysis.get_connection")
    def test_parse_args_updates_db_connection_string(self, mock_get_connection: MagicMock, mock_parse_args: MagicMock, analysis_script: AnalysisScript) -> None:
        """
        Test that parse_args updates the database connection string if specified in the arguments.
        """
        analysis_script.requires_db = True
        mock_parse_args.return_value = argparse.Namespace(log_level=None, config=None, db_connection_string="test_connection_string", llm_model=None)
        analysis_script.parse_args()
        mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
        assert analysis_script.db_conn == mock_get_connection.return_value

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.analysis.get_llm_client")
    def test_parse_args_updates_llm_model(self, mock_get_llm_client: MagicMock, mock_parse_args: MagicMock, analysis_script: AnalysisScript) -> None:
        """
        Test that parse_args updates the LLM model if specified in the arguments.
        """
        analysis_script.enable_llm = True
        mock_parse_args.return_value = argparse.Namespace(log_level=None, config=None, db_connection_string=None, llm_model="test_llm_model")
        analysis_script.parse_args()
        mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
        assert analysis_script.llm_client == mock_get_llm_client.return_value
