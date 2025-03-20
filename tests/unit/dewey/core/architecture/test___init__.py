import logging
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.architecture import ArchitectureModule
from dewey.core.base_script import BaseScript

# Constants
CONFIG_PATH = Path("/Users/srvo/dewey/config/dewey.yaml")


@pytest.fixture
def architecture_module() -> ArchitectureModule:
    """Fixture for creating an instance of ArchitectureModule."""
    return ArchitectureModule()


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture for creating a mock configuration dictionary."""
    return {
        'architecture': {
            'example_config': 'test_value'
        },
        'core': {
            'logging': {
                'level': 'DEBUG',
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'date_format': '%Y-%m-%d %H:%M:%S'
            }
        },
        'llm': {}
    }


@pytest.fixture
def mock_base_script(mock_config: Dict[str, Any]) -> MagicMock:
    """Fixture for mocking BaseScript."""
    with patch("dewey.core.architecture.BaseScript.__init__", return_value=None) as MockBaseScript:
        mock_base_script_instance = MagicMock()
        MockBaseScript.return_value = mock_base_script_instance
        mock_base_script_instance.config = mock_config
        mock_base_script_instance.logger = MagicMock()
        yield mock_base_script_instance


def test_architecture_module_initialization(mock_base_script: MagicMock) -> None:
    """Test the initialization of the ArchitectureModule."""
    module = ArchitectureModule()
    mock_base_script.logger.info.assert_called_with("Architecture module initialized.")
    assert module.name == "ArchitectureModule"
    assert module.config_section == "architecture"
    assert module.requires_db is True
    assert module.enable_llm is True


def test_run_method_success(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                           caplog: pytest.LogCaptureFixture) -> None:
    """Test the successful execution of the run method."""
    caplog.set_level(logging.INFO)

    architecture_module.get_config_value = MagicMock(return_value='test_value')
    architecture_module.db_conn = MagicMock()
    architecture_module.llm_client = MagicMock()

    architecture_module.run()

    assert "Example config value: test_value" in caplog.text
    assert "Database connection is available." in caplog.text
    assert "LLM client is available." in caplog.text
    assert "Architecture module run method executed." in caplog.text
    architecture_module.get_config_value.assert_called_with('example_config', default='default_value')


def test_run_method_no_db_connection(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                                     caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method when the database connection is not available."""
    caplog.set_level(logging.WARNING)
    architecture_module.get_config_value = MagicMock(return_value='test_value')
    architecture_module.db_conn = None
    architecture_module.llm_client = MagicMock()

    architecture_module.run()

    assert "Database connection is not available." in caplog.text


def test_run_method_no_llm_client(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                                      caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method when the LLM client is not available."""
    caplog.set_level(logging.WARNING)
    architecture_module.get_config_value = MagicMock(return_value='test_value')
    architecture_module.db_conn = MagicMock()
    architecture_module.llm_client = None

    architecture_module.run()

    assert "LLM client is not available." in caplog.text


def test_run_method_exception(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                              caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method when an exception occurs."""
    caplog.set_level(logging.ERROR)
    architecture_module.get_config_value = MagicMock(side_effect=ValueError("Test error"))

    architecture_module.run()

    assert "An error occurred during architecture module execution: Test error" in caplog.text
    assert "Traceback" in caplog.text


@patch("dewey.core.architecture.CONFIG_PATH", new=Path("nonexistent_config.yaml"))
def test_load_config_file_not_found(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading configuration when the file is not found."""
    caplog.set_level(logging.ERROR)
    with pytest.raises(FileNotFoundError):
        architecture_module._load_config()
    assert "Configuration file not found: nonexistent_config.yaml" in caplog.text


def test_load_config_yaml_error(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture,
                                tmp_path: Path) -> None:
    """Test loading configuration when the YAML is invalid."""
    caplog.set_level(logging.ERROR)
    config_file = tmp_path / "invalid_config.yaml"
    config_file.write_text("invalid: yaml: content")
    with patch("dewey.core.architecture.CONFIG_PATH", new=config_file):
        with pytest.raises(yaml.YAMLError):
            architecture_module._load_config()
        assert "Error parsing YAML configuration" in caplog.text


def test_load_config_specific_section(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                                      tmp_path: Path) -> None:
    """Test loading a specific section of the configuration."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    with patch("dewey.core.architecture.CONFIG_PATH", new=config_file):
        architecture_module.config_section = 'architecture'
        architecture_module.config = architecture_module._load_config()
        assert architecture_module.config == mock_config['architecture']


def test_load_config_specific_section_not_found(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                                                tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading a specific section of the configuration when the section is not found."""
    caplog.set_level(logging.WARNING)
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    with patch("dewey.core.architecture.CONFIG_PATH", new=config_file):
        architecture_module.config_section = 'nonexistent_section'
        architecture_module.config = architecture_module._load_config()
        assert architecture_module.config == mock_config
        assert "Config section 'nonexistent_section' not found in dewey.yaml. Using full config." in caplog.text


def test_get_config_value_existing_key(architecture_module: ArchitectureModule, mock_config: Dict[str, Any]) -> None:
    """Test getting an existing configuration value."""
    architecture_module.config = mock_config['architecture']
    value = architecture_module.get_config_value('example_config')
    assert value == 'test_value'


def test_get_config_value_default_value(architecture_module: ArchitectureModule, mock_config: Dict[str, Any]) -> None:
    """Test getting a configuration value with a default value."""
    architecture_module.config = mock_config['architecture']
    value = architecture_module.get_config_value('nonexistent_key', default='default_value')
    assert value == 'default_value'


def test_get_config_value_nested_key(architecture_module: ArchitectureModule, mock_config: Dict[str, Any]) -> None:
    """Test getting a nested configuration value."""
    architecture_module.config = mock_config
    value = architecture_module.get_config_value('core.logging.level')
    assert value == 'DEBUG'


def test_get_config_value_nested_key_missing(architecture_module: ArchitectureModule,
                                             mock_config: Dict[str, Any]) -> None:
    """Test getting a nested configuration value that is missing."""
    architecture_module.config = mock_config
    value = architecture_module.get_config_value('core.nonexistent_key', default='default_value')
    assert value == 'default_value'


def test_get_path_absolute_path(architecture_module: ArchitectureModule) -> None:
    """Test getting a path when an absolute path is provided."""
    absolute_path = '/absolute/path'
    path = architecture_module.get_path(absolute_path)
    assert path == Path(absolute_path)


def test_get_path_relative_path(architecture_module: ArchitectureModule) -> None:
    """Test getting a path when a relative path is provided."""
    relative_path = 'relative/path'
    expected_path = Path("/Users/srvo/dewey") / relative_path
    path = architecture_module.get_path(relative_path)
    assert path == expected_path


def test_setup_logging_from_config(architecture_module: ArchitectureModule, mock_config: Dict[str, Any],
                                  tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test setting up logging from the configuration file."""
    caplog.set_level(logging.DEBUG)
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    with patch("dewey.core.architecture.CONFIG_PATH", new=config_file):
        architecture_module._setup_logging()
        architecture_module.logger.debug("Test log message")
        assert "Test log message" in caplog.text


def test_setup_logging_default_config(architecture_module: ArchitectureModule, tmp_path: Path,
                                      caplog: pytest.LogCaptureFixture) -> None:
    """Test setting up logging with default configuration when the config file is missing."""
    caplog.set_level(logging.INFO)
    with patch("dewey.core.architecture.CONFIG_PATH", new=tmp_path / "nonexistent_config.yaml"):
        architecture_module._setup_logging()
        architecture_module.logger.info("Test log message")
        assert "Test log message" in caplog.text


@patch("dewey.core.architecture.get_connection")
def test_initialize_db_connection_success(mock_get_connection: MagicMock, architecture_module: ArchitectureModule,
                                          mock_config: Dict[str, Any]) -> None:
    """Test initializing the database connection successfully."""
    architecture_module.config = mock_config
    architecture_module._initialize_db_connection()
    mock_get_connection.assert_called()
    assert architecture_module.db_conn == mock_get_connection.return_value


@patch("dewey.core.architecture.get_connection", side_effect=ImportError)
def test_initialize_db_connection_import_error(mock_get_connection: MagicMock, architecture_module: ArchitectureModule,
                                               mock_config: Dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    """Test initializing the database connection when an ImportError occurs."""
    caplog.set_level(logging.ERROR)
    architecture_module.config = mock_config
    with pytest.raises(ImportError):
        architecture_module._initialize_db_connection()
    assert "Could not import database module. Is it installed?" in caplog.text


@patch("dewey.core.architecture.get_connection", side_effect=Exception("Test error"))
def test_initialize_db_connection_exception(mock_get_connection: MagicMock, architecture_module: ArchitectureModule,
                                            mock_config: Dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    """Test initializing the database connection when a general exception occurs."""
    caplog.set_level(logging.ERROR)
    architecture_module.config = mock_config
    with pytest.raises(Exception):
        architecture_module._initialize_db_connection()
    assert "Failed to initialize database connection: Test error" in caplog.text


@patch("dewey.core.architecture.get_llm_client")
def test_initialize_llm_client_success(mock_get_llm_client: MagicMock, architecture_module: ArchitectureModule,
                                           mock_config: Dict[str, Any]) -> None:
    """Test initializing the LLM client successfully."""
    architecture_module.config = mock_config
    architecture_module._initialize_llm_client()
    mock_get_llm_client.assert_called()
    assert architecture_module.llm_client == mock_get_llm_client.return_value


@patch("dewey.core.architecture.get_llm_client", side_effect=ImportError)
def test_initialize_llm_client_import_error(mock_get_llm_client: MagicMock, architecture_module: ArchitectureModule,
                                                mock_config: Dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    """Test initializing the LLM client when an ImportError occurs."""
    caplog.set_level(logging.ERROR)
    architecture_module.config = mock_config
    with pytest.raises(ImportError):
        architecture_module._initialize_llm_client()
    assert "Could not import LLM module. Is it installed?" in caplog.text


@patch("dewey.core.architecture.get_llm_client", side_effect=Exception("Test error"))
def test_initialize_llm_client_exception(mock_get_llm_client: MagicMock, architecture_module: ArchitectureModule,
                                             mock_config: Dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    """Test initializing the LLM client when a general exception occurs."""
    caplog.set_level(logging.ERROR)
    architecture_module.config = mock_config
    with pytest.raises(Exception):
        architecture_module._initialize_llm_client()
    assert "Failed to initialize LLM client: Test error" in caplog.text


def test_cleanup_db_connection(architecture_module: ArchitectureModule) -> None:
    """Test cleaning up the database connection."""
    architecture_module.db_conn = MagicMock()
    architecture_module._cleanup()
    architecture_module.db_conn.close.assert_called()


def test_cleanup_no_db_connection(architecture_module: ArchitectureModule) -> None:
    """Test cleaning up when there is no database connection."""
    architecture_module.db_conn = None
    architecture_module._cleanup()
    # Assert that close is not called when db_conn is None
    # We can't directly assert that close wasn't called, but we can assert that no exceptions were raised.
    assert True


def test_cleanup_db_connection_exception(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture) -> None:
    """Test cleaning up the database connection when an exception occurs."""
    caplog.set_level(logging.WARNING)
    architecture_module.db_conn = MagicMock()
    architecture_module.db_conn.close.side_effect = Exception("Test error")
    architecture_module._cleanup()
    assert "Error closing database connection: Test error" in caplog.text


def test_setup_argparse(architecture_module: ArchitectureModule) -> None:
    """Test setting up the argument parser."""
    parser = architecture_module.setup_argparse()
    assert parser.description == architecture_module.description
    assert parser.get_default("config") is None
    assert parser.get_default("log_level") is None


def test_parse_args_log_level(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing arguments and setting the log level."""
    caplog.set_level(logging.DEBUG)
    with patch("sys.argv", ["script_name", "--log-level", "DEBUG"]):
        args = architecture_module.parse_args()
        assert args.log_level == "DEBUG"
        assert architecture_module.logger.level == logging.DEBUG
        assert "Log level set to DEBUG" in caplog.text


def test_parse_args_config_file(architecture_module: ArchitectureModule, tmp_path: Path,
                               caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing arguments and loading a configuration file."""
    caplog.set_level(logging.INFO)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("test_key: test_value")
    with patch("sys.argv", ["script_name", "--config", str(config_file)]):
        args = architecture_module.parse_args()
        assert args.config == str(config_file)
        assert architecture_module.config == {"test_key": "test_value"}
        assert "Loaded configuration from" in caplog.text


def test_parse_args_config_file_not_found(architecture_module: ArchitectureModule, tmp_path: Path,
                                         caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing arguments when the configuration file is not found."""
    caplog.set_level(logging.ERROR)
    config_file = tmp_path / "nonexistent_config.yaml"
    with patch("sys.argv", ["script_name", "--config", str(config_file)]):
        with pytest.raises(SystemExit) as exc_info:
            architecture_module.parse_args()
        assert exc_info.value.code == 1
        assert "Configuration file not found:" in caplog.text


@patch("dewey.core.architecture.get_connection")
def test_parse_args_db_connection_string(mock_get_connection: MagicMock, architecture_module: ArchitectureModule,
                                         caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing arguments and setting the database connection string."""
    caplog.set_level(logging.INFO)
    architecture_module.requires_db = True
    with patch("sys.argv", ["script_name", "--db-connection-string", "test_connection_string"]):
        args = architecture_module.parse_args()
        assert args.db_connection_string == "test_connection_string"
        mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})
        assert architecture_module.db_conn == mock_get_connection.return_value
        assert "Using custom database connection" in caplog.text


@patch("dewey.core.architecture.get_llm_client")
def test_parse_args_llm_model(mock_get_llm_client: MagicMock, architecture_module: ArchitectureModule,
                              caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing arguments and setting the LLM model."""
    caplog.set_level(logging.INFO)
    architecture_module.enable_llm = True
    with patch("sys.argv", ["script_name", "--llm-model", "test_llm_model"]):
        args = architecture_module.parse_args()
        assert args.llm_model == "test_llm_model"
        mock_get_llm_client.assert_called_with({"model": "test_llm_model"})
        assert architecture_module.llm_client == mock_get_llm_client.return_value
        assert "Using custom LLM model:" in caplog.text


def test_execute_success(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture) -> None:
    """Test the successful execution of the execute method."""
    caplog.set_level(logging.INFO)
    architecture_module.parse_args = MagicMock()
    architecture_module.run = MagicMock()
    architecture_module._cleanup = MagicMock()

    architecture_module.execute()

    architecture_module.parse_args.assert_called()
    architecture_module.run.assert_called()
    architecture_module._cleanup.assert_called()
    assert "Starting execution of ArchitectureModule" in caplog.text
    assert "Completed execution of ArchitectureModule" in caplog.text


def test_execute_keyboard_interrupt(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture) -> None:
    """Test the execute method when a KeyboardInterrupt occurs."""
    caplog.set_level(logging.WARNING)
    architecture_module.parse_args = MagicMock()
    architecture_module.run = MagicMock(side_effect=KeyboardInterrupt)
    architecture_module._cleanup = MagicMock()

    with pytest.raises(SystemExit) as exc_info:
        architecture_module.execute()
    assert exc_info.value.code == 1
    assert "Script interrupted by user" in caplog.text
    architecture_module._cleanup.assert_called()


def test_execute_exception(architecture_module: ArchitectureModule, caplog: pytest.LogCaptureFixture) -> None:
    """Test the execute method when a general exception occurs."""
    caplog.set_level(logging.ERROR)
    architecture_module.parse_args = MagicMock()
    architecture_module.run = MagicMock(side_effect=Exception("Test error"))
    architecture_module._cleanup = MagicMock()

    with pytest.raises(SystemExit) as exc_info:
        architecture_module.execute()
    assert exc_info.value.code == 1
    assert "Error executing script: Test error" in caplog.text
    architecture_module._cleanup.assert_called()
