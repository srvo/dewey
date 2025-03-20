import logging
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.config import ConfigManager
from dewey.core.base_script import BaseScript

# Constants for test configuration
TEST_CONFIG_SECTION = "test_config"
TEST_KEY = "test_key"
TEST_DEFAULT_VALUE = "test_default_value"
TEST_VALUE = "test_value"
TEST_CONFIG_DATA = {TEST_CONFIG_SECTION: {TEST_KEY: TEST_VALUE}}
TEST_CONFIG_FILE = "test_config.yaml"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Sets up the test environment by creating a temporary config file."""
    # Create a temporary config file
    with open(TEST_CONFIG_FILE, "w") as f:
        yaml.dump(TEST_CONFIG_DATA, f)

    # Set environment variable for project root
    os.environ["PROJECT_ROOT"] = str(Path(".").resolve())

    yield  # Provide the fixture value

    # Teardown: Remove the temporary config file
    if os.path.exists(TEST_CONFIG_FILE):
        os.remove(TEST_CONFIG_FILE)
    if "PROJECT_ROOT" in os.environ:
        del os.environ["PROJECT_ROOT"]


class TestConfigManager:
    """Tests for the ConfigManager class."""

    @pytest.fixture
    def config_manager(self) -> ConfigManager:
        """Fixture to create a ConfigManager instance."""
        return ConfigManager(config_section=TEST_CONFIG_SECTION)

    def test_initialization(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the ConfigManager initializes correctly."""
        assert config_manager.config_section == TEST_CONFIG_SECTION
        assert "ConfigManager initialized." in caplog.text

    def test_run(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method of ConfigManager."""
        config_manager.run()
        assert "ConfigManager running." in caplog.text
        assert f"Example configuration value: {TEST_DEFAULT_VALUE}" in caplog.text

    def test_get_config_value(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test retrieving a configuration value."""
        value = config_manager.get_config_value(TEST_KEY)
        assert value == TEST_VALUE
        assert f"Retrieved config value for key '{TEST_KEY}': {value}" in caplog.text

    def test_get_config_value_default(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test retrieving a configuration value with a default."""
        value = config_manager.get_config_value("nonexistent_key", TEST_DEFAULT_VALUE)
        assert value == TEST_DEFAULT_VALUE
        assert f"Retrieved config value for key 'nonexistent_key': {value}" in caplog.text

    def test_config_section_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test when the specified config section is not found."""
        config_manager = ConfigManager(config_section="nonexistent_section")
        assert "Config section 'nonexistent_section' not found in dewey.yaml. Using full config." in caplog.text

    def test_config_file_not_found(self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when the configuration file is not found."""
        monkeypatch.setattr("dewey.core.config.CONFIG_PATH", Path("nonexistent_file.yaml"))
        with pytest.raises(FileNotFoundError):
            ConfigManager()
        assert "Configuration file not found: nonexistent_file.yaml" in caplog.text

    def test_invalid_yaml_config(self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when the configuration file contains invalid YAML."""
        # Create an invalid YAML file
        with open("invalid_config.yaml", "w") as f:
            f.write("invalid: yaml: content")

        monkeypatch.setattr("dewey.core.config.CONFIG_PATH", Path("invalid_config.yaml"))

        with pytest.raises(yaml.YAMLError):
            ConfigManager()
        assert "Error parsing YAML configuration" in caplog.text

        # Clean up the invalid YAML file
        if os.path.exists("invalid_config.yaml"):
            os.remove("invalid_config.yaml")

    def test_execute_method(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method of ConfigManager."""
        with patch.object(config_manager, 'parse_args') as mock_parse_args, \
             patch.object(config_manager, 'run') as mock_run:

            mock_parse_args.return_value = MagicMock()
            config_manager.execute()

            mock_parse_args.assert_called_once()
            mock_run.assert_called_once()
            assert "Starting execution of ConfigManager" in caplog.text
            assert "Completed execution of ConfigManager" in caplog.text

    def test_execute_keyboard_interrupt(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method handles KeyboardInterrupt."""
        with patch.object(config_manager, 'parse_args') as mock_parse_args, \
             patch.object(config_manager, 'run', side_effect=KeyboardInterrupt):

            mock_parse_args.return_value = MagicMock()
            with pytest.raises(SystemExit) as exc_info:
                config_manager.execute()

            assert exc_info.value.code == 1
            assert "Script interrupted by user" in caplog.text

    def test_execute_exception(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method handles exceptions."""
        with patch.object(config_manager, 'parse_args') as mock_parse_args, \
             patch.object(config_manager, 'run', side_effect=ValueError("Test Exception")):

            mock_parse_args.return_value = MagicMock()
            with pytest.raises(SystemExit) as exc_info:
                config_manager.execute()

            assert exc_info.value.code == 1
            assert "Error executing script: Test Exception" in caplog.text

    def test_get_path_absolute(self, config_manager: ConfigManager) -> None:
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path/to/file.txt"
        result = config_manager.get_path(absolute_path)
        assert str(result) == absolute_path

    def test_get_path_relative(self, config_manager: ConfigManager) -> None:
        """Test get_path method with a relative path."""
        relative_path = "relative/path/to/file.txt"
        expected_path = Path(os.environ["PROJECT_ROOT"]) / relative_path
        result = config_manager.get_path(relative_path)
        assert result == expected_path

    def test_get_config_value_nested(self, config_manager: ConfigManager) -> None:
        """Test retrieving a nested configuration value."""
        nested_config = {"level1": {"level2": {"level3": "nested_value"}}}
        config_manager.config = nested_config
        value = config_manager.get_config_value("level1.level2.level3")
        assert value == "nested_value"

    def test_get_config_value_nested_default(self, config_manager: ConfigManager) -> None:
        """Test retrieving a nested configuration value with a default."""
        config_manager.config = {}
        value = config_manager.get_config_value("level1.level2.level3", "default_value")
        assert value == "default_value"

    def test_get_config_value_type_error(self, config_manager: ConfigManager) -> None:
        """Test when a TypeError occurs while accessing the config."""
        config_manager.config = {"level1": "not_a_dict"}
        value = config_manager.get_config_value("level1.level2", "default_value")
        assert value == "default_value"

    def test_cleanup_db_connection(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _cleanup method closes the database connection."""
        mock_db_conn = MagicMock()
        config_manager.db_conn = mock_db_conn
        config_manager._cleanup()
        mock_db_conn.close.assert_called_once()
        assert "Closing database connection" in caplog.text

    def test_cleanup_db_connection_error(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _cleanup method handles errors when closing the database connection."""
        mock_db_conn = MagicMock()
        mock_db_conn.close.side_effect = Exception("Failed to close connection")
        config_manager.db_conn = mock_db_conn
        config_manager._cleanup()
        mock_db_conn.close.assert_called_once()
        assert "Error closing database connection: Failed to close connection" in caplog.text

    def test_setup_logging_from_config(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logging is set up correctly from the config file."""
        # Create a test config file with specific logging settings
        test_logging_config = {
            'core': {
                'logging': {
                    'level': 'DEBUG',
                    'format': '%(levelname)s - %(message)s',
                    'date_format': '%Y-%m-%d'
                }
            }
        }
        with open("test_logging_config.yaml", "w") as f:
            yaml.dump(test_logging_config, f)

        monkeypatch.setattr("dewey.core.config.CONFIG_PATH", Path("test_logging_config.yaml"))

        # Initialize ConfigManager
        config_manager = ConfigManager()

        # Check that the logger is configured as expected
        assert config_manager.logger.level == logging.DEBUG
        assert "%(levelname)s - %(message)s" in config_manager.logger.handlers[0].formatter._fmt

        # Clean up the test config file
        if os.path.exists("test_logging_config.yaml"):
            os.remove("test_logging_config.yaml")

    def test_setup_logging_default(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that default logging is set up when config is missing."""
        monkeypatch.setattr("dewey.core.config.CONFIG_PATH", Path("nonexistent_config.yaml"))

        # Initialize ConfigManager
        config_manager = ConfigManager()

        # Check that the logger is configured with default settings
        assert config_manager.logger.level == logging.INFO
        assert "%(asctime)s - %(levelname)s - %(name)s - %(message)s" in config_manager.logger.handlers[0].formatter._fmt

    def test_requires_db_flag(self) -> None:
        """Test that the requires_db flag is correctly set and used."""
        # Create a ConfigManager instance with requires_db=True
        config_manager_with_db = ConfigManager(requires_db=True)
        assert config_manager_with_db.requires_db is True
        assert config_manager_with_db.db_conn is not None  # Assuming _initialize_db_connection is called

        # Create a ConfigManager instance with requires_db=False
        config_manager_without_db = ConfigManager(requires_db=False)
        assert config_manager_without_db.requires_db is False
        assert config_manager_without_db.db_conn is None

    def test_enable_llm_flag(self) -> None:
        """Test that the enable_llm flag is correctly set and used."""
        # Create a ConfigManager instance with enable_llm=True
        config_manager_with_llm = ConfigManager(enable_llm=True)
        assert config_manager_with_llm.enable_llm is True
        assert config_manager_with_llm.llm_client is not None  # Assuming _initialize_llm_client is called

        # Create a ConfigManager instance with enable_llm=False
        config_manager_without_llm = ConfigManager(enable_llm=False)
        assert config_manager_without_llm.enable_llm is False
        assert config_manager_without_llm.llm_client is None

    def test_db_connection_failure(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that database connection failure is handled correctly."""
        # Mock the get_connection function to raise an exception
        monkeypatch.setattr("dewey.core.config.get_connection", side_effect=Exception("DB Connection Failed"))

        # Create a ConfigManager instance that requires a database connection
        with pytest.raises(Exception) as exc_info:
            ConfigManager(requires_db=True)

        # Assert that the exception is raised and the error is logged
        assert "Failed to initialize database connection: DB Connection Failed" in caplog.text
        assert str(exc_info.value) == "DB Connection Failed"

    def test_llm_client_failure(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that LLM client initialization failure is handled correctly."""
        # Mock the get_llm_client function to raise an exception
        monkeypatch.setattr("dewey.core.config.get_llm_client", side_effect=Exception("LLM Client Failed"))

        # Create a ConfigManager instance that requires an LLM client
        with pytest.raises(Exception) as exc_info:
            ConfigManager(enable_llm=True)

        # Assert that the exception is raised and the error is logged
        assert "Failed to initialize LLM client: LLM Client Failed" in caplog.text
        assert str(exc_info.value) == "LLM Client Failed"

    def test_db_import_error(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that an ImportError during database initialization is handled correctly."""
        # Mock the import of the database module to raise an ImportError
        monkeypatch.setattr("dewey.core.config.get_connection", side_effect=ImportError("No module named dewey.core.db"))

        # Create a ConfigManager instance that requires a database connection
        with pytest.raises(ImportError) as exc_info:
            ConfigManager(requires_db=True)

        # Assert that the ImportError is raised and the error is logged
        assert "Could not import database module. Is it installed?" in caplog.text
        assert str(exc_info.value) == "No module named dewey.core.db"

    def test_llm_import_error(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that an ImportError during LLM client initialization is handled correctly."""
        # Mock the import of the LLM module to raise an ImportError
        monkeypatch.setattr("dewey.core.config.get_llm_client", side_effect=ImportError("No module named dewey.llm"))

        # Create a ConfigManager instance that requires an LLM client
        with pytest.raises(ImportError) as exc_info:
            ConfigManager(enable_llm=True)

        # Assert that the ImportError is raised and the error is logged
        assert "Could not import LLM module. Is it installed?" in caplog.text
        assert str(exc_info.value) == "No module named dewey.llm"

    def test_parse_args_log_level(self, config_manager: ConfigManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the parse_args method updates the log level."""
        # Mock the setup_argparse and parse_args methods
        with patch.object(config_manager, 'setup_argparse') as mock_setup_argparse, \
             patch('argparse.ArgumentParser.parse_args') as mock_parse_args:

            # Create a mock argument parser and set the log_level argument
            mock_parser = MagicMock()
            mock_setup_argparse.return_value = mock_parser
            mock_parse_args.return_value = MagicMock(log_level="DEBUG")

            # Call the parse_args method
            config_manager.parse_args()

            # Assert that the log level is updated
            assert config_manager.logger.level == logging.DEBUG
            assert "Log level set to DEBUG" in caplog.text

    def test_parse_args_config_file(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the parse_args method loads a config file."""
        # Create a test config file
        test_config_data = {"test_key": "test_value"}
        with open("test_config_override.yaml", "w") as f:
            yaml.dump(test_config_data, f)

        # Mock the setup_argparse and parse_args methods
        with patch.object(config_manager, 'setup_argparse') as mock_setup_argparse, \
             patch('argparse.ArgumentParser.parse_args') as mock_parse_args:

            # Create a mock argument parser and set the config argument
            mock_parser = MagicMock()
            mock_setup_argparse.return_value = mock_parser
            mock_parse_args.return_value = MagicMock(config="test_config_override.yaml")

            # Call the parse_args method
            config_manager.parse_args()

            # Assert that the config is updated
            assert config_manager.config == test_config_data
            assert "Loaded configuration from test_config_override.yaml" in caplog.text

        # Clean up the test config file
        if os.path.exists("test_config_override.yaml"):
            os.remove("test_config_override.yaml")

    def test_parse_args_config_file_not_found(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the parse_args method handles a missing config file."""
        # Mock the setup_argparse and parse_args methods
        with patch.object(config_manager, 'setup_argparse') as mock_setup_argparse, \
             patch('argparse.ArgumentParser.parse_args') as mock_parse_args, \
             pytest.raises(SystemExit) as exc_info:

            # Create a mock argument parser and set the config argument
            mock_parser = MagicMock()
            mock_setup_argparse.return_value = mock_parser
            mock_parse_args.return_value = MagicMock(config="nonexistent_config.yaml")

            # Call the parse_args method
            config_manager.parse_args()

            # Assert that the SystemExit exception is raised
            assert exc_info.value.code == 1
            assert "Configuration file not found: nonexistent_config.yaml" in caplog.text

    def test_parse_args_db_connection_string(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the parse_args method updates the database connection string."""
        # Mock the setup_argparse and parse_args methods
        with patch.object(config_manager, 'setup_argparse') as mock_setup_argparse, \
             patch('argparse.ArgumentParser.parse_args') as mock_parse_args, \
             patch('dewey.core.config.get_connection') as mock_get_connection:

            # Create a mock argument parser and set the db_connection_string argument
            mock_parser = MagicMock()
            mock_setup_argparse.return_value = mock_parser
            mock_parse_args.return_value = MagicMock(db_connection_string="test_connection_string")

            # Set requires_db to True
            config_manager.requires_db = True

            # Call the parse_args method
            config_manager.parse_args()

            # Assert that the database connection is updated
            mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
            assert "Using custom database connection" in caplog.text

    def test_parse_args_llm_model(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the parse_args method updates the LLM model."""
        # Mock the setup_argparse and parse_args methods
        with patch.object(config_manager, 'setup_argparse') as mock_setup_argparse, \
             patch('argparse.ArgumentParser.parse_args') as mock_parse_args, \
             patch('dewey.core.config.get_llm_client') as mock_get_llm_client:

            # Create a mock argument parser and set the llm_model argument
            mock_parser = MagicMock()
            mock_setup_argparse.return_value = mock_parser
            mock_parse_args.return_value = MagicMock(llm_model="test_llm_model")

            # Set enable_llm to True
            config_manager.enable_llm = True

            # Call the parse_args method
            config_manager.parse_args()

            # Assert that the LLM model is updated
            mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
            assert "Using custom LLM model: test_llm_model" in caplog.text

    def test_setup_argparse(self, config_manager: ConfigManager) -> None:
        """Test that the setup_argparse method returns an ArgumentParser."""
        parser = config_manager.setup_argparse()
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description == config_manager.description

    def test_setup_argparse_db_args(self) -> None:
        """Test that the setup_argparse method adds database-specific arguments."""
        config_manager = ConfigManager(requires_db=True)
        parser = config_manager.setup_argparse()
        assert any(action.dest == "db_connection_string" for action in parser._actions)

    def test_setup_argparse_llm_args(self) -> None:
        """Test that the setup_argparse method adds LLM-specific arguments."""
        config_manager = ConfigManager(enable_llm=True)
        parser = config_manager.setup_argparse()
        assert any(action.dest == "llm_model" for action in parser._actions)

    def test_base_script_inheritance(self, config_manager: ConfigManager) -> None:
        """Test that ConfigManager inherits from BaseScript."""
        assert isinstance(config_manager, BaseScript)
