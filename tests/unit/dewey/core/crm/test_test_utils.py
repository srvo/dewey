"""Unit tests for dewey.core.crm.test_utils."""
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.research.utils.research_output_handler import (
    ResearchOutputHandler,
)
from dewey.core.research.utils.sts_xml_parser import STSXMLParser
from dewey.core.research.utils.universe_breakdown import UniverseBreakdown


class TestUniverseBreakdown:
    """Unit tests for the UniverseBreakdown class."""

    @pytest.fixture
    def breakdown(self) -> UniverseBreakdown:
        """Fixture to create a UniverseBreakdown instance."""
        return UniverseBreakdown()

    def test_analyze_universe_valid_data(self, breakdown: UniverseBreakdown) -> None:
        """Test analyze method with valid company data."""
        test_data: Dict[str, Any] = {
            "companies": [
                {"name": "Company A", "sector": "Technology", "market_cap": 1000000}, {"name": "Company B", "sector": "Healthcare", "market_cap": 2000000}, {"name": "Company C", "sector": "Technology", "market_cap": 1500000}, ]
        }
        analysis: Dict[str, Any] = breakdown.analyze(test_data)
        assert isinstance(analysis, dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        assert analysis["sector_breakdown"]["Technology"] == 2
        assert analysis["sector_breakdown"]["Healthcare"] == 1
        assert analysis["market_cap_distribution"]["large"] == 2
        assert analysis["market_cap_distribution"]["medium"] == 1

    def test_analyze_universe_empty_data(self, breakdown: UniverseBreakdown) -> None:
        """Test analyze method with empty company data."""
        test_data: Dict[str, Any]=None, Any] = breakdown.analyze(test_data)
        assert isinstance(analysis, dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        assert analysis["sector_breakdown"]=None, breakdown: UniverseBreakdown) -> None:
        """Test analyze method with missing fields in company data."""
        test_data: Dict[str, Any] = {
            "companies": [{"name": "Company A"}, {"sector": "Healthcare"}]
        }
        analysis: Dict[str, Any] = breakdown.analyze(test_data)
        assert isinstance(analysis, dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        # Expecting the missing fields to be ignored, resulting in empty breakdowns
        assert analysis["sector_breakdown"]=None, breakdown: UniverseBreakdown) -> None:
        """Test generate_report method with valid analysis data."""
        analysis_data: Dict[str, Any] = {
            "sector_breakdown": {"Technology": 2, "Healthcare": 1}, "market_cap_distribution": {"large": 1, "medium": 2}, }
        report: Dict[str, Any] = breakdown.generate_report(analysis_data)
        assert isinstance(report, dict)
        assert "summary" in report
        assert "charts" in report
        assert isinstance(report["charts"], list)

    def test_generate_report_empty_data(self, breakdown: UniverseBreakdown) -> None:
        """Test generate_report method with empty analysis data."""
        analysis_data: Dict[str, Any]=None, Any] = breakdown.generate_report(analysis_data)
        assert isinstance(report, dict)
        assert "summary" in report
        assert "charts" in report
        assert isinstance(report["charts"], list)
        assert report["summary"] == "No data to report."

    def test_generate_report_missing_fields(self, breakdown: UniverseBreakdown) -> None:
        """Test generate_report method with missing fields in analysis data."""
        analysis_data: Dict[str, Any] = {"sector_breakdown": {"Technology": 2}}
        report: Dict[str, Any] = breakdown.generate_report(analysis_data)
        assert isinstance(report, dict)
        assert "summary" in report
        assert "charts" in report
        assert isinstance(report["charts"], list)


class TestSTSXMLParser:
    """Unit tests for the STSXMLParser class."""

    @pytest.fixture
    def parser(self) -> STSXMLParser:
        """Fixture to create an STSXMLParser instance."""
        return STSXMLParser()

    def test_parse_xml_valid_xml(self, parser: STSXMLParser) -> None:
        """Test parse method with valid XML data."""
        test_xml: str = """
        <sts-analysis>
            <company>
                <name>Test Corp</name>
                <metrics>
                    <metric name="revenue">1000000</metric>
                    <metric name="profit">200000</metric>
                </metrics>
            </company>
        </sts-analysis>
        """
        result: Dict[str, Any] = parser.parse(test_xml)
        assert isinstance(result, dict)
        assert "company" in result
        assert result["company"]["name"] == "Test Corp"
        assert result["company"]["metrics"]["revenue"] == "1000000"

    def test_parse_xml_empty_xml(self, parser: STSXMLParser) -> None:
        """Test parse method with empty XML data."""
        test_xml: str = "<sts-analysis></sts-analysis>"
        result: Dict[str, Any] = parser.parse(test_xml)
        assert isinstance(result, dict)
        assert result=None, parser: STSXMLParser) -> None:
        """Test parse method with invalid XML data."""
        test_xml: str = "<invalid>xml</invalid>"
        with pytest.raises(ValueError):
            if Any] is None:
                Any] = {"companies": []}
        analysis: Dict[str
            if dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        assert analysis["sector_breakdown"] is None:
                dict)
        assert "sector_breakdown" in analysis
        assert "market_cap_distribution" in analysis
        assert analysis["sector_breakdown"] = = {}
        assert analysis["market_cap_distribution"] == {}

    def test_analyze_universe_missing_fields(self
            if resulting in empty breakdowns
        assert analysis["sector_breakdown"] is None:
                resulting in empty breakdowns
        assert analysis["sector_breakdown"] = = {}
        assert analysis["market_cap_distribution"] == {}

    def test_generate_report_valid_data(self
            if Any] is None:
                Any] = {}
        report: Dict[str
            if dict)
        assert result is None:
                dict)
        assert result = = {}

    def test_parse_xml_invalid_xml(self
            parser.parse(test_xml)

    def test_parse_xml_missing_elements(self, parser: STSXMLParser) -> None:
        """Test parse method with missing elements in XML data."""
        test_xml: str = """
        <sts-analysis>
            <company>
                <metrics>
                    <metric name="revenue">1000000</metric>
                </metrics>
            </company>
        </sts-analysis>
        """
        result: Dict[str, Any] = parser.parse(test_xml)
        assert isinstance(result, dict)
        assert "company" in result
        assert "name" not in result["company"]
        assert result["company"]["metrics"]["revenue"] == "1000000"


class TestResearchOutputHandler:
    """Unit tests for the ResearchOutputHandler class."""

    @pytest.fixture
    def handler(self) -> ResearchOutputHandler:
        """Fixture to create a ResearchOutputHandler instance."""
        return ResearchOutputHandler()

    @pytest.fixture
    def tmp_path(self, tmp_path: Path) -> Path:
        """Fixture to create a temporary directory."""
        return tmp_path

    def test_save_output_valid_data(
        self, handler: ResearchOutputHandler, tmp_path: Path
    ) -> None:
        """Test save method with valid data."""
        test_data: Dict[str, Any] = {
            "analysis": {"score": 85, "recommendations": ["Test recommendation"]}, "timestamp": "2024-03-19T12:00:00", }
        output_path: Path = tmp_path / "test_output.json"
        handler.save(test_data, output_path)
        assert output_path.exists()
        with open(output_path) as f:
            saved_data: Dict[str, Any] = json.load(f)
        assert saved_data == test_data

    def test_save_output_empty_data(
        self, handler: ResearchOutputHandler, tmp_path: Path
    ) -> None:
        """Test save method with empty data."""
        test_data: Dict[str, Any]=None, output_path)
        assert output_path.exists()
        with open(output_path) as f:
            saved_data: Dict[str, Any] = json.load(f)
        assert saved_data == test_data

    def test_load_output_valid_file(
        self, handler: ResearchOutputHandler, tmp_path: Path
    ) -> None:
        """Test load method with a valid file."""
        test_data: Dict[str, Any] = {
            "analysis": {"score": 85, "recommendations": ["Test recommendation"]}
        }
        output_path: Path = tmp_path / "test_output.json"
        with open(output_path, "w") as f:
            json.dump(test_data, f)
        loaded_data: Dict[str, Any] = handler.load(output_path)
        assert loaded_data == test_data

    def test_load_output_nonexistent_file(
        self, handler: ResearchOutputHandler
    ) -> None:
        """Test load method with a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            if Any] is None:
                Any] = {}
        output_path: Path = tmp_path / "test_output.json"
        handler.save(test_data
            handler.load(Path("nonexistent.json"))

    def test_load_output_invalid_json(
        self, handler: ResearchOutputHandler, tmp_path: Path
    ) -> None:
        """Test load method with an invalid JSON file."""
        output_path: Path = tmp_path / "test_output.json"
        with open(output_path, "w") as f:
            f.write("invalid json")
        with pytest.raises(json.JSONDecodeError):
            handler.load(output_path)


class TestBaseScript:
    """Unit tests for the BaseScript class."""

    class DummyScript(BaseScript):
        """A dummy script class for testing BaseScript."""

        def __init__(self, config_section: str = "test_config") -> None:
            """Initialize the DummyScript."""
            super().__init__(config_section=config_section)

        def run(self) -> None:
            """Dummy run method."""
            pass

    @pytest.fixture
    def dummy_script(self) -> DummyScript:
        """Fixture to create a DummyScript instance."""
        return TestBaseScript.DummyScript()

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Fixture to create a mock configuration dictionary."""
        return {
            "test_config": {"param1": "value1", "param2": 123},
            "logging": {"level": "DEBUG", "format": "%(message)s"},
        }

    @patch("dewey.core.base_script.yaml.safe_load")
    @patch("dewey.core.base_script.open", create=True)
    def test_load_config_valid_config(
        self, mock_open: Any, mock_safe_load: Any, dummy_script: DummyScript, mock_config: Dict[str, Any]
    ) -> None:
        """Test loading configuration from a valid YAML file."""
        mock_safe_load.return_value = mock_config
        mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump(mock_config)

        config = dummy_script._load_config()
        assert config == mock_config["test_config"]
        mock_open.assert_called_once()
        mock_safe_load.assert_called_once()

    @patch("dewey.core.base_script.yaml.safe_load")
    @patch("dewey.core.base_script.open", create=True)
    def test_load_config_missing_section(
        self, mock_open: Any, mock_safe_load: Any, dummy_script: DummyScript, mock_config: Dict[str, Any]
    ) -> None:
        """Test loading configuration with a missing section."""
        mock_safe_load.return_value = mock_config
        mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump(mock_config)
        dummy_script.config_section = "nonexistent_section"
        config = dummy_script._load_config()
        assert config == mock_config
        mock_open.assert_called_once()
        mock_safe_load.assert_called_once()

    @patch("dewey.core.base_script.open", side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_open: Any, dummy_script: DummyScript) -> None:
        """Test loading configuration when the file is not found."""
        with pytest.raises(FileNotFoundError):
            dummy_script._load_config()
        mock_open.assert_called_once()

    @patch("dewey.core.base_script.yaml.safe_load", side_effect=yaml.YAMLError)
    @patch("dewey.core.base_script.open", create=True)
    def test_load_config_invalid_yaml(
        self, mock_open: Any, mock_safe_load: Any, dummy_script: DummyScript, mock_config: Dict[str, Any]
    ) -> None:
        """Test loading configuration with invalid YAML."""
        mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump(mock_config)
        with pytest.raises(yaml.YAMLError):
            dummy_script._load_config()
        mock_open.assert_called_once()
        mock_safe_load.assert_called_once()

    @patch("dewey.core.base_script.logging.basicConfig")
    def test_setup_logging_from_config(self, mock_basicConfig: Any, dummy_script: DummyScript, mock_config: Dict[str, Any]) -> None:
        """Test setting up logging from the configuration file."""
        with patch("dewey.core.base_script.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump({"core": {"logging": mock_config["logging"]}})
            dummy_script._setup_logging()
            mock_basicConfig.assert_called_once_with(
                level=logging.DEBUG, format="%(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            assert isinstance(dummy_script.logger, logging.Logger)

    @patch("dewey.core.base_script.logging.basicConfig")
    def test_setup_logging_default_config(self, mock_basicConfig: Any, dummy_script: DummyScript) -> None:
        """Test setting up logging with default configuration."""
        with patch("dewey.core.base_script.open", side_effect=FileNotFoundError):
            dummy_script._setup_logging()
            mock_basicConfig.assert_called_once_with(
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            assert isinstance(dummy_script.logger, logging.Logger)

    def test_get_path_absolute_path(self, dummy_script: DummyScript) -> None:
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path"
        result = dummy_script.get_path(absolute_path)
        assert result == Path(absolute_path)

    def test_get_path_relative_path(self, dummy_script: DummyScript) -> None:
        """Test get_path method with a relative path."""
        relative_path = "relative/path"
        result = dummy_script.get_path(relative_path)
        assert result == BaseScript.PROJECT_ROOT / relative_path

    @patch.object(BaseScript, '_load_config')
    def test_get_config_value_existing_key(self, mock_load_config: Any, dummy_script: DummyScript) -> None:
        """Test get_config_value method with an existing key."""
        mock_load_config.return_value = {"llm": {"model": "test_model"}}
        dummy_script.config = mock_load_config.return_value
        result = dummy_script.get_config_value("llm.model")
        assert result == "test_model"

    @patch.object(BaseScript, '_load_config')
    def test_get_config_value_missing_key(self, mock_load_config: Any, dummy_script: DummyScript) -> None:
        """Test get_config_value method with a missing key."""
        mock_load_config.return_value = {"llm": {"model": "test_model"}}
        dummy_script.config = mock_load_config.return_value
        result = dummy_script.get_config_value("llm.nonexistent_key", "default_value")
        assert result == "default_value"

    @patch.object(BaseScript, '_load_config')
    def test_get_config_value_nested_missing_key(self, mock_load_config: Any, dummy_script: DummyScript) -> None:
        """Test get_config_value method with a nested missing key."""
        mock_load_config.return_value = {"llm": {"model": "test_model"}}
        dummy_script.config = mock_load_config.return_value
        result = dummy_script.get_config_value("nonexistent_section.nonexistent_key", "default_value")
        assert result == "default_value"
