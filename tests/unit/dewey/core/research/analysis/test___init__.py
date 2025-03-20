import pytest
from unittest.mock import patch, MagicMock
import logging
from dewey.core.research.analysis import AnalysisScript
from dewey.core.base_script import BaseScript
from pathlib import Path
import yaml
from typing import Any, Dict


class TestAnalysisScript:
    """Tests for the AnalysisScript class."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Fixture to provide a mock configuration."""
        return {"test_key": "test_value"}

    @pytest.fixture
    def analysis_script(self, mock_config: Dict[str, Any]) -> AnalysisScript:
        """Fixture to create an AnalysisScript instance with a mock config section."""
        with patch.object(BaseScript, '_load_config', return_value=mock_config):
            script = AnalysisScript(config_section="test_section")
            return script

    def test_analysis_script_initialization(self, analysis_script: AnalysisScript) -> None:
        """Test that AnalysisScript initializes correctly."""
        assert analysis_script.config_section == "test_section"
        assert analysis_script.name == "AnalysisScript"
        assert analysis_script.logger is not None
        assert analysis_script.config is not None

    def test_analysis_script_initialization_no_config_section(self) -> None:
        """Test that AnalysisScript initializes correctly without a config section."""
        with patch.object(BaseScript, '_load_config', return_value={}):
            script = AnalysisScript()
            assert script.config_section == "analysis"
            assert script.name == "AnalysisScript"
            assert script.logger is not None
            assert script.config is not None

    def test_run_method_raises_not_implemented_error(self, analysis_script: AnalysisScript) -> None:
        """Test that the run method raises a NotImplementedError."""
        with pytest.raises(NotImplementedError):
            analysis_script.run()

    def test_config_loaded_correctly(self, analysis_script: AnalysisScript, mock_config: Dict[str, Any]) -> None:
        """Test that the config is loaded correctly."""
        assert analysis_script.config == mock_config

    def test_logging_setup(self) -> None:
        """Test that logging is set up correctly."""
        with patch.object(BaseScript, '_load_config', return_value={}):
            script = AnalysisScript()
            assert isinstance(script.logger, logging.Logger)

    def test_get_path_absolute(self, analysis_script: AnalysisScript) -> None:
        """Test get_path with an absolute path."""
        absolute_path = "/absolute/path"
        assert analysis_script.get_path(absolute_path) == Path(absolute_path)

    def test_get_path_relative(self, analysis_script: AnalysisScript) -> None:
        """Test get_path with a relative path."""
        relative_path = "relative/path"
        expected_path = Path(__file__).parent.parent.parent.parent.joinpath(relative_path)
        assert analysis_script.get_path(relative_path) == expected_path

    def test_get_config_value_existing_key(self, analysis_script: AnalysisScript, mock_config: Dict[str, Any]) -> None:
        """Test get_config_value with an existing key."""
        assert analysis_script.get_config_value("test_key") == "test_value"

    def test_get_config_value_nested_key(self) -> None:
        """Test get_config_value with a nested key."""
        mock_config = {"nested": {"key": "nested_value"}}
        with patch.object(BaseScript, '_load_config', return_value=mock_config):
            script = AnalysisScript()
            assert script.get_config_value("nested.key") == "nested_value"

    def test_get_config_value_default_value(self, analysis_script: AnalysisScript) -> None:
        """Test get_config_value with a default value."""
        assert analysis_script.get_config_value("non_existent_key", "default_value") == "default_value"

    def test_get_config_value_non_existent_key(self, analysis_script: AnalysisScript) -> None:
        """Test get_config_value with a non-existent key and no default value."""
        assert analysis_script.get_config_value("non_existent_key") is None

    @patch("dewey.core.research.analysis.BaseScript._load_config")
    def test_config_section_not_found(self, mock_load_config: MagicMock, analysis_script: AnalysisScript) -> None:
        """Test that a warning is logged when the config section is not found."""
        mock_load_config.return_value = {"another_section": {"key": "value"}}
        with patch.object(analysis_script.logger, "warning") as mock_warning:
            analysis_script._load_config()
            mock_warning.assert_called_once()

    @patch("dewey.core.research.analysis.yaml.safe_load")
    @patch("dewey.core.research.analysis.open", create=True)
    def test_load_config_file_not_found(self, mock_open: MagicMock, mock_safe_load: MagicMock, analysis_script: AnalysisScript) -> None:
        """Test that FileNotFoundError is raised when the config file is not found."""
        mock_open.side_effect = FileNotFoundError
        with pytest.raises(FileNotFoundError):
            analysis_script._load_config()

    @patch("dewey.core.research.analysis.yaml.safe_load")
    @patch("dewey.core.research.analysis.open", create=True)
    def test_load_config_yaml_error(self, mock_open: MagicMock, mock_safe_load: MagicMock, analysis_script: AnalysisScript) -> None:
        """Test that yaml.YAMLError is raised when the config file is invalid YAML."""
        mock_safe_load.side_effect = yaml.YAMLError
        with pytest.raises(yaml.YAMLError):
            analysis_script._load_config()
