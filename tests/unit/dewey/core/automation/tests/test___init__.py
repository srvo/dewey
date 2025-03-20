"""Tests for dewey.core.automation.tests.__init__.py."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml
import pandas as pd

# Assuming BaseScript is in the parent directory of 'automation'
sys.path.append(str(Path(__file__).resolve().parents[4] / "src"))
from dewey.core.base_script import BaseScript  # noqa: E402
import dewey.core.automation.tests.__init__ as automation_module
from dewey.core.automation.tests.__init__ import DataAnalysisScript, main  # noqa: E402


# Mock the CONFIG_PATH to avoid actual file access
@pytest.fixture(autouse=True)
def mock_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Fixture to mock the CONFIG_PATH."""
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    monkeypatch.setattr("dewey.core.base_script.CONFIG_PATH", config_path)


class MockBaseScript(BaseScript):
    """Mock BaseScript class for testing."""

    def __init__(self, config_section: str = None, requires_db: bool = False, enable_llm: bool = False):
        super().__init__(config_section=config_section, requires_db=requires_db, enable_llm=enable_llm)

    def run(self) -> None:
        """Mock run method."""
        pass


# Tests for DataAnalysisScript
class TestDataAnalysisScript:
    """Tests for the DataAnalysisScript class."""

    @pytest.fixture
    def mock_data_analysis_script(self, mock_config: Dict[str, Any]) -> DataAnalysisScript:
        """Fixture to create a DataAnalysisScript instance with mocked dependencies."""
        with patch("dewey.core.automation.tests.__init__.DatabaseConnection"), \
             patch("dewey.core.automation.tests.__init__.LLMClient"):
            script = DataAnalysisScript()
            script.config = mock_config
            script.logger = MagicMock()
            script.llm_client = MagicMock()
            script.db_conn = MagicMock()
            return script

    @patch("dewey.core.automation.tests.__init__.DatabaseConnection")
    def test_fetch_data_from_db_success(self, mock_db_connection: MagicMock, mock_data_analysis_script: DataAnalysisScript) -> None:
        """Test that fetch_data_from_db successfully fetches data."""
        mock_db_conn = MagicMock()
        mock_execute = MagicMock()
        mock_fetchall = MagicMock()
        mock_fetchall.return_value = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
        mock_execute.return_value.fetchall = mock_fetchall
        mock_db_conn.return_value.__enter__.return_value.execute = mock_execute
        mock_db_connection.return_value = mock_db_conn

        data = mock_data_analysis_script.fetch_data_from_db()

        assert "data" in data
        assert data["data"] == [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
        mock_data_analysis_script.logger.info.assert_called_once()

    @patch("dewey.core.automation.tests.__init__.DatabaseConnection", side_effect=Exception("DB Error"))
    def test_fetch_data_from_db_failure(self, mock_db_connection: MagicMock, mock_data_analysis_script: DataAnalysisScript, caplog: pytest.LogCaptureFixture) -> None:
        """Test that fetch_data_from_db handles database errors."""
        caplog.set_level(logging.ERROR)
        with pytest.raises(Exception, match="DB Error"):
            mock_data_analysis_script.fetch_data_from_db()
        assert "Error fetching data from database" in caplog.text

    def test_analyze_data_with_llm_success(self, mock_data_analysis_script: DataAnalysisScript) -> None:
        """Test that analyze_data_with_llm successfully analyzes data."""
        mock_data_analysis_script.llm_client.generate_text.return_value = "Test analysis"
        data = {"data": "test data"}
        analysis = mock_data_analysis_script.analyze_data_with_llm(data)

        assert "analysis" in analysis
        assert analysis["analysis"] == "Test analysis"
        mock_data_analysis_script.logger.info.assert_called_once()

    def test_analyze_data_with_llm_no_llm_client(self, mock_data_analysis_script: DataAnalysisScript, caplog: pytest.LogCaptureFixture) -> None:
        """Test that analyze_data_with_llm handles missing LLM client."""
        caplog.set_level(logging.ERROR)
        mock_data_analysis_script.llm_client = None
        data = {"data": "test data"}
        with pytest.raises(ValueError, match="LLM client is not initialized."):
            mock_data_analysis_script.analyze_data_with_llm(data)
        assert "Error analyzing data with LLM" not in caplog.text

    def test_analyze_data_with_llm_failure(self, mock_data_analysis_script: DataAnalysisScript, caplog: pytest.LogCaptureFixture) -> None:
        """Test that analyze_data_with_llm handles LLM errors."""
        caplog.set_level(logging.ERROR)
        mock_data_analysis_script.llm_client.generate_text.side_effect = Exception("LLM Error")
        data = {"data": "test data"}
        with pytest.raises(Exception, match="LLM Error"):
            mock_data_analysis_script.analyze_data_with_llm(data)
        assert "Error analyzing data with LLM" in caplog.text

    @patch.object(DataAnalysisScript, "fetch_data_from_db")
    @patch.object(DataAnalysisScript, "analyze_data_with_llm")
    def test_run_success(self, mock_analyze_data: MagicMock, mock_fetch_data: MagicMock, mock_data_analysis_script: DataAnalysisScript) -> None:
        """Test that run executes successfully."""
        mock_fetch_data.return_value = {"data": "test data"}
        mock_analyze_data.return_value = {"analysis": "test analysis"}

        mock_data_analysis_script.run()

        mock_fetch_data.assert_called_once()
        mock_analyze_data.assert_called_once_with({"data": "test data"})
        assert mock_data_analysis_script.logger.info.call_count == 3

    @patch.object(DataAnalysisScript, "fetch_data_from_db", side_effect=Exception("Fetch Error"))
    def test_run_fetch_failure(self, mock_fetch_data: MagicMock, mock_data_analysis_script: DataAnalysisScript, caplog: pytest.LogCaptureFixture) -> None:
        """Test that run handles fetch data errors."""
        caplog.set_level(logging.ERROR)
        mock_data_analysis_script.run()
        assert "Script failed" in caplog.text

    def test_setup_argparse(self, mock_data_analysis_script: DataAnalysisScript) -> None:
        """Test that setup_argparse returns an ArgumentParser."""
        parser = mock_data_analysis_script.setup_argparse()
        assert isinstance(parser, argparse.ArgumentParser)
        assert any(action.dest == "input" for action in parser._actions)

# Tests for main function
class TestMainFunction:
    """Tests for the main function."""

    @patch("dewey.core.automation.tests.__init__.DataAnalysisScript")
    def test_main_executes_script(self, mock_script_class: MagicMock) -> None:
        """Test that main function executes the DataAnalysisScript."""
        mock_script = MagicMock()
        mock_script_class.return_value = mock_script

        main()

        mock_script.execute.assert_called_once()


# Tests for module-level functions (if any)
class TestModuleFunctions:
    """Tests for module-level functions."""

    @patch("dewey.core.automation.tests.__init__.DataAnalysisScript")
    @patch("sys.argv", ["__init__.py", "--input", "test_input"])
    def test_main_with_input(self, mock_script_class: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test main function with input argument."""
        caplog.set_level(logging.INFO)
        mock_script = MagicMock()
        mock_script_class.return_value = mock_script

        automation_module.main()

        mock_script.execute.assert_called_once()

    @patch("dewey.core.automation.tests.__init__.DataAnalysisScript")
    @patch("sys.argv", ["__init__.py"])
    def test_main_no_input(self, mock_script_class: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """Test main function with no input argument."""
        caplog.set_level(logging.INFO)
        mock_script = MagicMock()
        mock_script_class.return_value = mock_script

        automation_module.main()

        mock_script.execute.assert_called_once()

    @patch("dewey.core.automation.tests.__init__.DatabaseConnection")
    def test_fetch_data_from_db(self, mock_db_connection: MagicMock, capfd: pytest.CaptureFixture[str]) -> None:
        """Test fetch_data_from_db function."""
        mock_db_conn = MagicMock()
        mock_execute = MagicMock()
        mock_fetchall = MagicMock()
        mock_fetchall.return_value = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
        mock_execute.return_value.fetchall = mock_fetchall
        mock_db_conn.return_value.__enter__.return_value.execute = mock_execute
        mock_db_connection.return_value = mock_db_conn
        script = DataAnalysisScript()
        script.config = {}
        script.logger = MagicMock()
        result = script.fetch_data_from_db()
        captured = capfd.readouterr()

        assert "data" in result
        assert result["data"] == [{"id": 1, "value": 10}, {"id": 2, "value": 20}]

    @patch("dewey.llm.llm_utils.LLMClient.generate_text")
    def test_analyze_data_with_llm(self, mock_llm_generate: MagicMock, capfd: pytest.CaptureFixture[str]) -> None:
        """Test analyze_data_with_llm function."""
        mock_llm_generate.return_value = "some analysis"
        script = DataAnalysisScript()
        script.config = {}
        script.logger = MagicMock()
        script.llm_client = MagicMock()
        data = {"data": "some data"}
        result = script.analyze_data_with_llm(data)
        captured = capfd.readouterr()

        assert "analysis" in result
        assert result["analysis"] == "some analysis"

