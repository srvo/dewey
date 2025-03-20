import logging
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from dewey.core.config.config import Config
from dewey.core.base_script import BaseScript

# Constants
CONFIG_FILE = Path("/Users/srvo/dewey/config/dewey.yaml")


# Fixtures
@pytest.fixture
def config_instance() -> Config:
    """Fixture to provide an instance of the Config class."""
    return Config()


@pytest.fixture
def mock_config_file(tmp_path: Path) -> Path:
    """Fixture to create a temporary config file for testing."""
    config_data = {
        "core": {
            "example_key": "test_value",
            "logging": {"level": "DEBUG"},
        }
    }
    config_file = tmp_path / "dewey.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    return config_file


@pytest.fixture
def base_script_instance() -> BaseScript:
    """Fixture to provide an instance of the BaseScript class."""
    class TestScript(BaseScript):
        def run(self):
            pass
    return TestScript()


# Tests
def test_config_initialization(config_instance: Config) -> None:
    """Test that the Config object is initialized correctly."""
    assert config_instance.name == "Config"
    assert config_instance.config_section == "core"
    assert config_instance.logger is not None


def test_config_run(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method of the Config class."""
    with caplog.at_level(logging.INFO):
        config_instance.run()
    assert "Example config value: default_value" in caplog.text
    assert "Current log level: INFO" in caplog.text


def test_config_run_with_config_value(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method of the Config class with a config value."""
    config_instance.config = {"example_key": "test_value", "logging": {"level": "DEBUG"}}
    with caplog.at_level(logging.INFO):
        config_instance.run()
    assert "Example config value: test_value" in caplog.text
    assert "Current log level: INFO" in caplog.text


def test_config_run_exception(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method of the Config class when an exception occurs."""
    config_instance.get_config_value = lambda *args, **kwargs: raise Exception("Test exception")
    with caplog.at_level(logging.ERROR):
        config_instance.run()
    assert "An error occurred: Test exception" in caplog.text


def test_get_config_value(config_instance: Config) -> None:
    """Test the get_config_value method."""
    config_instance.config = {"llm": {"model": "test_model"}}
    value = config_instance.get_config_value("llm.model")
    assert value == "test_model"


def test_get_config_value_default(config_instance: Config) -> None:
    """Test the get_config_value method with a default value."""
    value = config_instance.get_config_value("nonexistent_key", "default_value")
    assert value == "default_value"


def test_get_config_value_nested(config_instance: Config) -> None:
    """Test the get_config_value method with a nested key."""
    config_instance.config = {"nested": {"key": {"value": "nested_value"}}}
    value = config_instance.get_config_value("nested.key.value")
    assert value == "nested_value"


def test_get_config_value_missing_nested(config_instance: Config) -> None:
    """Test the get_config_value method with a missing nested key."""
    config_instance.config = {"nested": {}}
    value = config_instance.get_config_value("nested.key.value", "default_value")
    assert value == "default_value"


def test_load_config_success(config_instance: Config, mock_config_file: Path) -> None:
    """Test loading the configuration successfully."""
    config_instance.config_section = "core"
    with patch("dewey.core.config.config.CONFIG_PATH", mock_config_file):
        config = config_instance._load_config()
        assert isinstance(config, dict)
        assert config["example_key"] == "test_value"


def test_load_config_section_not_found(config_instance: Config, mock_config_file: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading the configuration when the specified section is not found."""
    config_instance.config_section = "nonexistent_section"
    with patch("dewey.core.config.config.CONFIG_PATH", mock_config_file), caplog.at_level(logging.WARNING):
        config = config_instance._load_config()
        assert isinstance(config, dict)
        assert "example_key" in config["core"]


def test_load_config_file_not_found(config_instance: Config, tmp_path: Path) -> None:
    """Test loading the configuration when the file is not found."""
    config_instance.config_section = "core"
    config_file = tmp_path / "nonexistent_config.yaml"
    with patch("dewey.core.config.config.CONFIG_PATH", config_file), pytest.raises(FileNotFoundError):
        config_instance._load_config()


def test_load_config_invalid_yaml(config_instance: Config, tmp_path: Path) -> None:
    """Test loading the configuration with invalid YAML."""
    config_file = tmp_path / "invalid_config.yaml"
    with open(config_file, "w") as f:
        f.write("invalid: yaml: content")

    with patch("dewey.core.config.config.CONFIG_PATH", config_file), pytest.raises(yaml.YAMLError):
        config_instance._load_config()


def test_setup_logging(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test setting up logging."""
    config_instance._setup_logging()
    with caplog.at_level(logging.INFO):
        config_instance.logger.info("Test log message")
    assert "Test log message" in caplog.text


def test_setup_logging_config_error(config_instance: Config, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test setting up logging when there's an error loading the config."""
    config_file = tmp_path / "nonexistent_config.yaml"
    with patch("dewey.core.config.config.CONFIG_PATH", config_file), caplog.at_level(logging.INFO):
        config_instance._setup_logging()
        config_instance.logger.info("Test log message")
    assert "Test log message" in caplog.text


def test_get_path_absolute(config_instance: Config) -> None:
    """Test get_path with an absolute path."""
    absolute_path = "/absolute/path"
    result = config_instance.get_path(absolute_path)
    assert result == Path(absolute_path)


def test_get_path_relative(config_instance: Config) -> None:
    """Test get_path with a relative path."""
    relative_path = "relative/path"
    expected_path = Path("/Users/srvo/dewey") / relative_path
    result = config_instance.get_path(relative_path)
    assert result == expected_path


def test_execute_keyboard_interrupt(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test execute method when a KeyboardInterrupt occurs."""
    config_instance.parse_args = lambda: None
    config_instance.run = lambda: raise KeyboardInterrupt
    with caplog.at_level(logging.WARNING), pytest.raises(SystemExit) as exc_info:
        config_instance.execute()
    assert "Script interrupted by user" in caplog.text
    assert exc_info.value.code == 1


def test_execute_exception(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test execute method when an exception occurs."""
    config_instance.parse_args = lambda: None
    config_instance.run = lambda: raise ValueError("Test error")
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc_info:
        config_instance.execute()
    assert "Error executing script: Test error" in caplog.text
    assert exc_info.value.code == 1


def test_cleanup(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test the _cleanup method."""
    # Mock a database connection
    class MockDBConnection:
        def close(self):
            pass

    mock_db_conn = MockDBConnection()
    config_instance.db_conn = mock_db_conn

    with patch.object(mock_db_conn, 'close') as mock_close, caplog.at_level(logging.DEBUG):
        config_instance._cleanup()
        mock_close.assert_called_once()
    assert "Closing database connection" in caplog.text


def test_cleanup_no_db_conn(config_instance: Config) -> None:
    """Test the _cleanup method when there is no database connection."""
    config_instance.db_conn = None
    config_instance._cleanup()  # Should not raise any exceptions


def test_cleanup_db_conn_error(config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test the _cleanup method when closing the database connection raises an exception."""
    class MockDBConnection:
        def close(self):
            raise Exception("Failed to close connection")

    mock_db_conn = MockDBConnection()
    config_instance.db_conn = mock_db_conn

    with caplog.at_level(logging.WARNING):
        config_instance._cleanup()
    assert "Error closing database connection: Failed to close connection" in caplog.text


def test_setup_argparse(config_instance: Config) -> None:
    """Test the setup_argparse method."""
    parser = config_instance.setup_argparse()
    assert parser.description == config_instance.description
    assert parser.arguments[0].dest == "config"
    assert parser.arguments[1].dest == "log_level"


def test_setup_argparse_with_db(base_script_instance: BaseScript) -> None:
    """Test the setup_argparse method when database is required."""
    base_script_instance.requires_db = True
    parser = base_script_instance.setup_argparse()
    assert parser.arguments[0].dest == "config"
    assert parser.arguments[1].dest == "log_level"
    assert parser.arguments[2].dest == "db_connection_string"


def test_setup_argparse_with_llm(base_script_instance: BaseScript) -> None:
    """Test the setup_argparse method when LLM is enabled."""
    base_script_instance.enable_llm = True
    parser = base_script_instance.setup_argparse()
    assert parser.arguments[0].dest == "config"
    assert parser.arguments[1].dest == "log_level"
    assert parser.arguments[2].dest == "llm_model"


@patch("argparse.ArgumentParser.parse_args")
def test_parse_args_log_level(mock_parse_args, config_instance: Config, caplog: pytest.LogCaptureFixture) -> None:
    """Test the parse_args method when log level is specified."""
    mock_parse_args.return_value = argparse.Namespace(log_level="DEBUG", config=None)
    config_instance.parse_args()
    assert config_instance.logger.level == logging.DEBUG


@patch("argparse.ArgumentParser.parse_args")
def test_parse_args_config_file(mock_parse_args, config_instance: Config, mock_config_file: Path) -> None:
    """Test the parse_args method when a config file is specified."""
    mock_parse_args.return_value = argparse.Namespace(log_level=None, config=str(mock_config_file))
    config_instance.parse_args()
    assert config_instance.config["example_key"] == "test_value"


@patch("argparse.ArgumentParser.parse_args")
def test_parse_args_config_file_not_found(mock_parse_args, config_instance: Config, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test the parse_args method when the config file is not found."""
    config_file = tmp_path / "nonexistent_config.yaml"
    mock_parse_args.return_value = argparse.Namespace(log_level=None, config=str(config_file))
    with pytest.raises(SystemExit) as exc_info:
        config_instance.parse_args()
    assert exc_info.value.code == 1


@patch("argparse.ArgumentParser.parse_args")
def test_parse_args_db_connection_string(mock_parse_args, base_script_instance: BaseScript) -> None:
    """Test the parse_args method when a database connection string is specified."""
    base_script_instance.requires_db = True
    mock_parse_args.return_value = argparse.Namespace(log_level=None, config=None, db_connection_string="test_connection_string")
    with patch("dewey.core.base_script.get_connection") as mock_get_connection:
        base_script_instance.parse_args()
        mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})


@patch("argparse.ArgumentParser.parse_args")
def test_parse_args_llm_model(mock_parse_args, base_script_instance: BaseScript) -> None:
    """Test the parse_args method when an LLM model is specified."""
    base_script_instance.enable_llm = True
    mock_parse_args.return_value = argparse.Namespace(log_level=None, config=None, llm_model="test_llm_model")
    with patch("dewey.core.base_script.get_llm_client") as mock_get_llm_client:
        base_script_instance.parse_args()
        mock_get_llm_client.assert_called_with({"model": "test_llm_model"})


def test_base_script_initialization(base_script_instance: BaseScript) -> None:
    """Test that the BaseScript object is initialized correctly."""
    assert base_script_instance.name == "TestScript"
    assert base_script_instance.config is not None
    assert base_script_instance.logger is not None


def test_base_script_initialization_with_params() -> None:
    """Test that the BaseScript object is initialized correctly with params."""
    class TestScript(BaseScript):
        def run(self):
            pass
    test_script_instance = TestScript(name="CustomName", description="Custom Description", config_section="custom_section", requires_db=True, enable_llm=True)
    assert test_script_instance.name == "CustomName"
    assert test_script_instance.description == "Custom Description"
    assert test_script_instance.config_section == "custom_section"
    assert test_script_instance.requires_db == True
    assert test_script_instance.enable_llm == True
    assert test_script_instance.logger is not None


def test_base_script_initialization_db_import_error(caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript initialization when database module cannot be imported."""
    with patch("dewey.core.base_script.get_connection", side_effect=ImportError("No module named 'dewey.core.db'")):
        class TestScript(BaseScript):
            def run(self):
                pass
        with pytest.raises(ImportError) as exc_info:
            TestScript(requires_db=True)
        assert "Could not import database module. Is it installed?" in str(exc_info.value)


def test_base_script_initialization_llm_import_error(caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript initialization when LLM module cannot be imported."""
    with patch("dewey.core.base_script.get_llm_client", side_effect=ImportError("No module named 'dewey.llm'")):
        class TestScript(BaseScript):
            def run(self):
                pass
        with pytest.raises(ImportError) as exc_info:
            TestScript(enable_llm=True)
        assert "Could not import LLM module. Is it installed?" in str(exc_info.value)


def test_base_script_initialization_db_connection_error(caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript initialization when database connection fails."""
    with patch("dewey.core.base_script.get_connection", side_effect=Exception("Database connection failed")):
        class TestScript(BaseScript):
            def run(self):
                pass
        with pytest.raises(Exception) as exc_info:
            TestScript(requires_db=True)
        assert "Failed to initialize database connection: Database connection failed" in str(exc_info.value)


def test_base_script_initialization_llm_client_error(caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript initialization when LLM client initialization fails."""
    with patch("dewey.core.base_script.get_llm_client", side_effect=Exception("LLM client failed")):
        class TestScript(BaseScript):
            def run(self):
                pass
        with pytest.raises(Exception) as exc_info:
            TestScript(enable_llm=True)
        assert "Failed to initialize LLM client: LLM client failed" in str(exc_info.value)
