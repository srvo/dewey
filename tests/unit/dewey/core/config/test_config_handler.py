"""Tests for dewey.core.config.config_handler."""

import logging
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any
import os

import pytest
import yaml

from dewey.core.config.config_handler import ConfigHandler
from dewey.core.base_script import BaseScript


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "test_value"
    mock_script.logger = MagicMock()
    return mock_script


@pytest.fixture
def config_handler() -> ConfigHandler:
    """Fixture for creating a ConfigHandler instance."""
    return ConfigHandler()


class TestConfigHandler:
    """Tests for the ConfigHandler class."""

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_initialization(self, mock_init, config_handler: ConfigHandler):
        """Test that the ConfigHandler is initialized correctly."""
        assert isinstance(config_handler, ConfigHandler)
        assert config_handler.config_section == "config_handler"
        assert config_handler.name == "ConfigHandler"
        assert config_handler.logger is not None
        assert isinstance(config_handler.logger, logging.Logger)
        assert config_handler.config is not None

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_run_method(self, mock_init, config_handler: ConfigHandler, caplog):
        """Test that the run method logs the correct message."""
        with caplog.at_level(logging.INFO):
            config_handler.run()
        assert "ConfigHandler is running." in caplog.text

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_existing_key(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns the correct value for an existing key."""
        mock_get_config_value.return_value = "test_value"
        value = config_handler.get_value("test_key")
        assert value == "test_value"

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_non_existing_key(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns the default value for a non-existing key."""
        mock_get_config_value.return_value = None
        value = config_handler.get_value("non_existing_key", default="default_value")
        assert value == "default_value"

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_no_default(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns None when the key is not found and no default is provided."""
        mock_get_config_value.return_value = None
        value = config_handler.get_value("non_existing_key")
        assert value is None

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_nested_key(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value can retrieve nested configuration values."""
        mock_get_config_value.return_value = {"nested_key": "nested_value"}
        value = config_handler.get_value("nested_key.nested_key")
        assert value == {"nested_key": "nested_value"}

    @patch("dewey.core.base_script.CONFIG_PATH", "test_config.yaml")
    @patch("dewey.core.base_script.yaml.safe_load")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_config_handler_with_specific_config_section(
        self, mock_init, mock_safe_load
    ):
        """Test ConfigHandler with a specific config section."""
        config_section_name = "test_config_section"
        test_config_data = {
            config_section_name: {"param1": "value1", "param2": 123}
        }
        mock_safe_load.return_value = test_config_data

        config_handler = ConfigHandler()
        config_handler.config_section = config_section_name
        config_handler.config = config_handler._load_config()

        assert config_handler.config["param1"] == "value1"
        assert config_handler.config["param2"] == 123

    @patch("dewey.core.base_script.CONFIG_PATH", "test_config.yaml")
    @patch("dewey.core.base_script.yaml.safe_load")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_config_handler_missing_config_section(
        self, mock_init, mock_safe_load, caplog
    ):
        """Test ConfigHandler when the specified config section is missing."""
        config_section_name = "missing_section"
        test_config_data = {"other_section": {"param1": "value1"}}
        mock_safe_load.return_value = test_config_data

        with caplog.at_level(logging.WARNING):
            config_handler = ConfigHandler()
            config_handler.config_section = config_section_name
            config_handler.config = config_handler._load_config()

        assert (
            f"Config section '{config_section_name}' not found in dewey.yaml. Using full config."
            in caplog.text
        )
        assert config_handler.config == test_config_data

    @patch("dewey.core.base_script.CONFIG_PATH", "nonexistent_config.yaml")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    @patch("os.path.exists")
    def test_config_handler_file_not_found_error(
        self, mock_exists, mock_init, caplog
    ):
        """Test ConfigHandler when the configuration file is not found."""
        mock_exists.return_value = False
        with pytest.raises(FileNotFoundError) as excinfo:
            config_handler = ConfigHandler()
            with caplog.at_level(logging.ERROR):
                config_handler._load_config()

        assert "Configuration file not found: nonexistent_config.yaml" in caplog.text
        assert "No such file or directory" in str(excinfo.value)

    @patch("dewey.core.base_script.CONFIG_PATH", "invalid_config.yaml")
    @patch("dewey.core.base_script.yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML"))
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    @patch("os.path.exists")
    def test_config_handler_yaml_error(
        self, mock_exists, mock_init, mock_safe_load, caplog
    ):
        """Test ConfigHandler when the configuration file contains invalid YAML."""
        mock_exists.return_value = True
        with pytest.raises(yaml.YAMLError) as excinfo:
            config_handler = ConfigHandler()
            with caplog.at_level(logging.ERROR):
                config_handler._load_config()

        assert "Error parsing YAML configuration: Invalid YAML" in caplog.text
        assert "Invalid YAML" in str(excinfo.value)

    @patch("dewey.core.base_script.CONFIG_PATH", "test_config.yaml")
    @patch("builtins.open", new_callable=mock_open, read_data="test_config_data")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    @patch("os.path.exists")
    def test_config_handler_load_config_success(
        self, mock_exists, mock_init, mock_open_file, caplog
    ):
        """Test ConfigHandler when the configuration file is loaded successfully."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = "test_config_data"

        config_handler = ConfigHandler()
        with caplog.at_level(logging.DEBUG):
            config_handler._load_config()

        assert f"Loading configuration from {config_handler.CONFIG_PATH}" in caplog.text

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_config_handler_name_override(self, mock_init):
        """Test that the ConfigHandler name can be overridden."""
        custom_name = "CustomConfigHandler"
        config_handler = ConfigHandler()
        config_handler.name = custom_name
        assert config_handler.name == custom_name

    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_config_handler_description(self, mock_init):
        """Test that the ConfigHandler description can be set."""
        custom_description = "Custom description for ConfigHandler"
        config_handler = ConfigHandler()
        config_handler.description = custom_description
        assert config_handler.description == custom_description

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_empty_key(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns the default value when an empty key is provided."""
        mock_get_config_value.return_value = "test_value"
        default_value = "default_value"
        value = config_handler.get_value("", default=default_value)
        assert value == default_value

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_empty_key_no_default(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns None when an empty key is provided and no default is provided."""
        mock_get_config_value.return_value = "test_value"
        value = config_handler.get_value("")
        assert value is None

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_nested_key_missing_intermediate(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns the default value when a nested key is missing an intermediate level."""
        mock_get_config_value.return_value = {}
        default_value = "default_value"
        value = config_handler.get_value("missing.nested.key", default=default_value)
        assert value == default_value

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_nested_key_missing_intermediate_no_default(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns None when a nested key is missing an intermediate level and no default is provided."""
        mock_get_config_value.return_value = {}
        value = config_handler.get_value("missing.nested.key")
        assert value is None

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_nested_key_empty_intermediate(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns the default value when a nested key has an empty intermediate level."""
        mock_get_config_value.return_value = {"": "intermediate_value"}
        default_value = "default_value"
        value = config_handler.get_value(".nested.key", default=default_value)
        assert value == default_value

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
    def test_get_value_nested_key_empty_intermediate_no_default(
        self, mock_init, mock_get_config_value, config_handler: ConfigHandler
    ):
        """Test that get_value returns None when a nested key has an empty intermediate level and no default is provided."""
        mock_get_config_value.return_value = {"": "intermediate_value"}
        value = config_handler.get_value(".nested.key")
        assert value is None
