"""Tests for the ConfigProcessor class."""

import io
import pytest
from pathlib import Path
from dewey.unit/config.unit/config_handler import ConfigProcessor

@pytest.fixture
def unit/config_processor():
    """Fixture providing a ConfigProcessor instance."""
    return ConfigProcessor()

@pytest.fixture
def sample_yaml_data():
    """Fixture providing sample YAML data."""
    return """
core:
  project_root: /Users/srvo/dewey
  backup_strategy: 3-2-1
  default_timezone: UTC
logging:
  level: INFO
  format: '%(asctime)s - %(levelname)s - %(message)s'
"""

@pytest.fixture
def sample_toml_data():
    """Fixture providing sample TOML data."""
    return """
[core]
project_root = "/Users/srvo/dewey"
backup_strategy = "3-2-1"
default_timezone = "UTC"

[logging]
level = "INFO"
format = "%(asctime)s - %(levelname)s - %(message)s"
"""

class TestConfigProcessor:
    """Test cases for ConfigProcessor class."""

    def test_init(self, unit/config_processor):
        """Test initialization of ConfigProcessor."""
        assert unit/config_processor.settings == {}
        assert unit/config_processor.parser is None

    def test_parse_yaml(self, unit/config_processor, sample_yaml_data):
        """Test parsing YAML data."""
        stream = io.StringIO(sample_yaml_data)
        result = unit/config_processor.parse(stream)
        
        assert isinstance(result, dict)
        assert result["core"]["project_root"] == "/Users/srvo/dewey"
        assert result["logging"]["level"] == "INFO"

    def test_parse_toml(self, unit/config_processor, sample_toml_data):
        """Test parsing TOML data."""
        stream = io.StringIO(sample_toml_data)
        result = unit/config_processor.parse(stream)
        
        assert isinstance(result, dict)
        assert result["core"]["project_root"] == "/Users/srvo/dewey"
        assert result["logging"]["level"] == "INFO"

    def test_parse_invalid_data(self, unit/config_processor):
        """Test parsing invalid data raises ValueError."""
        invalid_data = "This is not YAML or TOML"
        stream = io.StringIO(invalid_data)
        
        with pytest.raises(ValueError):
            unit/config_processor.parse(stream)

    def test_serialize(self, unit/config_processor):
        """Test serialization of unit/configuration data."""
        data = {
            "core": {
                "project_root": "/Users/srvo/dewey",
                "backup_strategy": "3-2-1"
            }
        }
        result = unit/config_processor.serialize(data)
        
        assert isinstance(result, str)
        assert "core:" in result
        assert "project_root: /Users/srvo/dewey" in result

    def test_is_quoted(self, unit/config_processor):
        """Test quote detection in strings."""
        assert unit/config_processor.is_quoted('"test"')
        assert unit/config_processor.is_quoted("'test'")
        assert unit/config_processor.is_quoted('"""test"""', triple=True)
        assert not unit/config_processor.is_quoted("test")
        assert not unit/config_processor.is_quoted("")

    def test_unquote_str(self, unit/config_processor):
        """Test string unquoting."""
        assert unit/config_processor.unquote_str('"test"') == "test"
        assert unit/config_processor.unquote_str("'test'") == "test"
        assert unit/config_processor.unquote_str('"""test"""', triple=True) == "test"
        assert unit/config_processor.unquote_str("test") == "test"

    def test_parse_toml_section_name(self, unit/config_processor):
        """Test parsing TOML section names."""
        assert unit/config_processor.parse_toml_section_name('"core"') == "core"
        assert unit/config_processor.parse_toml_section_name("logging") == "logging"

    def test_get_toml_section(self, unit/config_processor):
        """Test retrieving TOML sections."""
        data = {
            "core": {"project_root": "/Users/srvo/dewey"},
            "logging": {"level": "INFO"}
        }
        
        assert unit/config_processor.get_toml_section(data, "core") == {"project_root": "/Users/srvo/dewey"}
        assert unit/config_processor.get_toml_section(data, '"logging"') == {"level": "INFO"}
        assert unit/config_processor.get_toml_section(data, "nonexistent") is None

    def test_command_line_key_conversion(self, unit/config_processor):
        """Test conversion of unit/config keys to command line arguments."""
        assert unit/config_processor.get_command_line_key_for_unknown_unit/config_file_setting("projectRoot") == "--project_root"
        assert unit/config_processor.get_command_line_key_for_unknown_unit/config_file_setting("backupStrategy") == "--backup_strategy"

    def test_convert_item_to_command_line_arg(self, unit/config_processor):
        """Test conversion of unit/config items to command line arguments."""
        assert unit/config_processor.convert_item_to_command_line_arg("store", "projectRoot", "/path") == "--project_root /path"
        assert unit/config_processor.convert_item_to_command_line_arg("store_true", "debug", True) == "--debug"
        assert unit/config_processor.convert_item_to_command_line_arg("store", "verbose", True) == "--verbose true" 