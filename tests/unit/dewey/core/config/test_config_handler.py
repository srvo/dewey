import logging
from unittest.mock import patch

import pytest
import yaml

from dewey.core.config.config_handler import ConfigHandler
from dewey.core.base_script import BaseScript


class TestConfigHandler:
    """Tests for the ConfigHandler class."""

    @pytest.fixture
    def config_handler(self):
        """Fixture for creating a ConfigHandler instance."""
        return ConfigHandler()

    def test_initialization(self, config_handler: ConfigHandler):
        """Test that the ConfigHandler is initialized correctly."""
        assert isinstance(config_handler, ConfigHandler)
        assert config_handler.config_section == "config_handler"
        assert config_handler.name == "ConfigHandler"
        assert config_handler.logger is not None
        assert isinstance(config_handler.logger, logging.Logger)
        assert config_handler.config is not None

    def test_run_method(self, config_handler: ConfigHandler, caplog):
        """Test that the run method logs the correct message."""
        with caplog.at_level(logging.INFO):
            config_handler.run()
        assert "ConfigHandler is running." in caplog.text

    def test_get_value_existing_key(self, config_handler: ConfigHandler):
        """Test that get_value returns the correct value for an existing key."""
        # Assuming there's a key "test_key" in the config
        with patch.object(BaseScript, "get_config_value", return_value="test_value"):
            value = config_handler.get_value("test_key")
        assert value == "test_value"

    def test_get_value_non_existing_key(self, config_handler: ConfigHandler):
        """Test that get_value returns the default value for a non-existing key."""
        with patch.object(BaseScript, "get_config_value", return_value=None):
            value = config_handler.get_value(
                "non_existing_key", default="default_value"
            )
        assert value == "default_value"

    def test_get_value_no_default(self, config_handler: ConfigHandler):
        """Test that get_value returns None when the key is not found and no default is provided."""
        with patch.object(BaseScript, "get_config_value", return_value=None):
            value = config_handler.get_value("non_existing_key")
        assert value is None

    def test_get_value_nested_key(self, config_handler: ConfigHandler):
        """Test that get_value can retrieve nested configuration values."""
        with patch.object(
            BaseScript, "get_config_value", return_value={"nested_key": "nested_value"}
        ):
            value = config_handler.get_value("nested_key.nested_key")
        assert value == {"nested_key": "nested_value"}

    def test_config_handler_with_specific_config_section(self):
        """Test ConfigHandler with a specific config section."""
        config_section_name = "test_config_section"
        test_config_data = {config_section_name: {"param1": "value1", "param2": 123}}

        with (
            patch("dewey.core.base_script.CONFIG_PATH", "test_config.yaml"),
            patch(
                "dewey.core.base_script.yaml.safe_load", return_value=test_config_data
            ),
        ):
            config_handler = ConfigHandler()
            config_handler.config_section = config_section_name
            config_handler.config = config_handler._load_config()

            assert config_handler.config["param1"] == "value1"
            assert config_handler.config["param2"] == 123

    def test_config_handler_missing_config_section(self, caplog):
        """Test ConfigHandler when the specified config section is missing."""
        config_section_name = "missing_section"
        test_config_data = {"other_section": {"param1": "value1"}}

        with (
            patch("dewey.core.base_script.CONFIG_PATH", "test_config.yaml"),
            patch(
                "dewey.core.base_script.yaml.safe_load", return_value=test_config_data
            ),
            caplog.at_level(logging.WARNING),
        ):
            config_handler = ConfigHandler()
            config_handler.config_section = config_section_name
            config_handler.config = config_handler._load_config()

            assert (
                "Config section 'missing_section' not found in dewey.yaml. Using full config."
                in caplog.text
            )
            assert config_handler.config == test_config_data

    def test_config_handler_file_not_found_error(self, caplog):
        """Test ConfigHandler when the configuration file is not found."""
        with (
            patch("dewey.core.base_script.CONFIG_PATH", "nonexistent_config.yaml"),
            pytest.raises(FileNotFoundError) as excinfo,
        ):
            config_handler = ConfigHandler()
            with caplog.at_level(logging.ERROR):
                config_handler._load_config()

        assert "Configuration file not found: nonexistent_config.yaml" in caplog.text
        assert "No such file or directory" in str(excinfo.value)

    def test_config_handler_yaml_error(self, caplog):
        """Test ConfigHandler when the configuration file contains invalid YAML."""
        with (
            patch("dewey.core.base_script.CONFIG_PATH", "invalid_config.yaml"),
            patch(
                "dewey.core.base_script.yaml.safe_load",
                side_effect=yaml.YAMLError("Invalid YAML"),
            ),
            pytest.raises(yaml.YAMLError) as excinfo,
        ):
            config_handler = ConfigHandler()
            with caplog.at_level(logging.ERROR):
                config_handler._load_config()

        assert "Error parsing YAML configuration: Invalid YAML" in caplog.text
        assert "Invalid YAML" in str(excinfo.value)
