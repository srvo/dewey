import logging
from unittest.mock import patch

import pytest

from dewey.core.research.analysis.company_analysis import CompanyAnalysis


class TestCompanyAnalysis:
    """Unit tests for the CompanyAnalysis class."""

    @pytest.fixture
    def company_analysis(self) -> CompanyAnalysis:
        """Fixture to create a CompanyAnalysis instance."""
        return CompanyAnalysis()

    def test_init(self, company_analysis: CompanyAnalysis) -> None:
        """Test the initialization of the CompanyAnalysis class."""
        assert company_analysis.name == "CompanyAnalysis"
        assert company_analysis.description is None
        assert company_analysis.config_section == "company_analysis"
        assert company_analysis.requires_db is False
        assert company_analysis.enable_llm is False
        assert isinstance(company_analysis.logger, logging.Logger)
        assert company_analysis.config is not None
        assert company_analysis.db_conn is None
        assert company_analysis.llm_client is None

    @patch("dewey.core.research.analysis.company_analysis.CompanyAnalysis.logger")
    def test_run(self, mock_logger, company_analysis: CompanyAnalysis) -> None:
        """Test the run method of the CompanyAnalysis class."""
        company_analysis.run()
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Starting company analysis...")
        mock_logger.info.assert_any_call("Company analysis completed.")

    def test_config_section_override(self) -> None:
        """Test that the config section can be overridden."""
        analysis = CompanyAnalysis()
        assert analysis.config == analysis._load_config()["company_analysis"]

        analysis = CompanyAnalysis(config_section="test_config")
        assert analysis.config == analysis._load_config()["test_config"]

    def test_config_section_missing(self, caplog) -> None:
        """Test that a warning is logged when the config section is missing."""
        caplog.set_level(logging.WARNING)
        analysis = CompanyAnalysis(config_section="missing_config")
        assert "Config section 'missing_config' not found in dewey.yaml" in caplog.text
        assert analysis.config == analysis._load_config()

    @patch("dewey.core.research.analysis.company_analysis.load_dotenv")
    @patch("dewey.core.research.analysis.company_analysis.yaml.safe_load")
    def test_load_config_file_not_found(self, mock_safe_load, mock_load_dotenv, caplog) -> None:
        """Test that FileNotFoundError is raised when the config file is not found."""
        caplog.set_level(logging.ERROR)
        mock_safe_load.side_effect = FileNotFoundError("config/dewey.yaml")
        with pytest.raises(FileNotFoundError):
            CompanyAnalysis()
        assert "Configuration file not found: /Users/srvo/dewey/config/dewey.yaml" in caplog.text

    @patch("dewey.core.research.analysis.company_analysis.load_dotenv")
    @patch("dewey.core.research.analysis.company_analysis.yaml.safe_load")
    def test_load_config_yaml_error(self, mock_safe_load, mock_load_dotenv, caplog) -> None:
        """Test that yaml.YAMLError is raised when the config file is invalid."""
        caplog.set_level(logging.ERROR)
        mock_safe_load.side_effect = Exception("Invalid YAML")
        with pytest.raises(Exception):
            CompanyAnalysis()
        assert "Error parsing YAML configuration: Invalid YAML" in caplog.text
