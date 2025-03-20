import logging
from unittest.mock import patch

import pytest

from dewey.core.research.companies.company_views import CompanyViews


class TestCompanyViews:
    """Unit tests for the CompanyViews class."""

    @pytest.fixture
    def company_views(self) -> CompanyViews:
        """Fixture to create a CompanyViews instance."""
        return CompanyViews()

    def test_init(self, company_views: CompanyViews) -> None:
        """Test the __init__ method."""
        assert company_views.name == "CompanyViews"
        assert company_views.config_section == "company_views"
        assert company_views.logger is not None

    @patch("dewey.core.research.companies.company_views.CompanyViews.logger")
    def test_run(self, mock_logger: logging.Logger, company_views: CompanyViews) -> None:
        """Test the run method."""
        company_views.run()
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2
        assert "Starting company views management..." in mock_logger.info.call_args_list[0][0][0]
        assert "Company views management completed." in mock_logger.info.call_args_list[1][0][0]

    @patch("dewey.core.research.companies.company_views.CONFIG_PATH")
    def test_load_config_success(self, mock_config_path, company_views: CompanyViews, tmp_path) -> None:
        """Test loading configuration successfully."""
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / "test_config.yaml"
        mock_config_path = config_file
        with open(config_file, "w") as f:
            import yaml
            yaml.dump(config_data, f)

        company_views.CONFIG_PATH = config_file
        config = company_views._load_config()
        assert config == config_data

    @patch("dewey.core.research.companies.company_views.CONFIG_PATH")
    def test_load_config_filenotfound(self, mock_config_path, company_views: CompanyViews) -> None:
        """Test loading configuration when the file is not found."""
        mock_config_path.exists.return_value = False
        company_views.CONFIG_PATH = "nonexistent_config.yaml"
        with pytest.raises(FileNotFoundError):
            company_views._load_config()

    @patch("dewey.core.research.companies.company_views.CONFIG_PATH")
    def test_load_config_yamLError(self, mock_config_path, company_views: CompanyViews, tmp_path) -> None:
        """Test loading configuration when the YAML is invalid."""
        config_file = tmp_path / "invalid_config.yaml"
        with open(config_file, "w") as f:
            f.write("invalid yaml content")

        company_views.CONFIG_PATH = config_file
        with pytest.raises(Exception):
            company_views._load_config()

    @patch("dewey.core.research.companies.company_views.BaseScript._initialize_db_connection")
    def test_init_requires_db(self, mock_init_db, company_views: CompanyViews) -> None:
        """Test initializing CompanyViews with database requirement."""
        company_views = CompanyViews()
        company_views.requires_db = True
        company_views.__init__()
        assert mock_init_db.called

    @patch("dewey.core.research.companies.company_views.BaseScript._initialize_llm_client")
    def test_init_enable_llm(self, mock_init_llm, company_views: CompanyViews) -> None:
        """Test initializing CompanyViews with LLM enabled."""
        company_views = CompanyViews()
        company_views.enable_llm = True
        company_views.__init__()
        assert mock_init_llm.called

    def test_get_path_absolute(self, company_views: CompanyViews) -> None:
        """Test get_path with an absolute path."""
        absolute_path = "/absolute/path"
        result = company_views.get_path(absolute_path)
        assert str(result) == absolute_path

    def test_get_path_relative(self, company_views: CompanyViews) -> None:
        """Test get_path with a relative path."""
        relative_path = "relative/path"
        expected_path = company_views.PROJECT_ROOT / relative_path
        result = company_views.get_path(relative_path)
        assert result == expected_path

    def test_get_config_value_existing_key(self, company_views: CompanyViews) -> None:
        """Test get_config_value with an existing key."""
        company_views.config = {"level1": {"level2": "value"}}
        result = company_views.get_config_value("level1.level2")
        assert result == "value"

    def test_get_config_value_missing_key(self, company_views: CompanyViews) -> None:
        """Test get_config_value with a missing key."""
        company_views.config = {"level1": {"level2": "value"}}
        result = company_views.get_config_value("level1.level3", "default")
        assert result == "default"

    def test_get_config_value_missing_level(self, company_views: CompanyViews) -> None:
        """Test get_config_value with a missing level."""
        company_views.config = {"level1": {"level2": "value"}}
        result = company_views.get_config_value("level3.level4", "default")
        assert result == "default"
