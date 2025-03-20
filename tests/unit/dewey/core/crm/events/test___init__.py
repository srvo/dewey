import logging
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.crm.events import EventsModule


@pytest.fixture
def events_module(mocker: MagicMock) -> EventsModule:
    """Fixture for creating an EventsModule instance with mocked dependencies."""
    mocker.patch("dewey.core.crm.events.EventsModule._setup_logging")
    mocker.patch("dewey.core.crm.events.EventsModule._load_config")
    mocker.patch("dewey.core.crm.events.EventsModule._initialize_db_connection")
    mocker.patch("dewey.core.crm.events.EventsModule._initialize_llm_client")
    module = EventsModule()
    module.logger = mocker.MagicMock()
    module.config = {}
    module.db_conn = mocker.MagicMock()
    module.llm_client = mocker.MagicMock()
    return module


def test_events_module_initialization(mocker: MagicMock) -> None:
    """Test the initialization of the EventsModule."""
    mocker.patch("dewey.core.crm.events.EventsModule._setup_logging")
    mocker.patch("dewey.core.crm.events.EventsModule._load_config")
    mocker.patch("dewey.core.crm.events.EventsModule._initialize_db_connection")
    mocker.patch("dewey.core.crm.events.EventsModule._initialize_llm_client")

    module = EventsModule(
        name="TestModule",
        description="Test Description",
        config_section="test_config",
        requires_db=False,
        enable_llm=False,
    )

    assert module.name == "TestModule"
    assert module.description == "Test Description"
    assert module.config_section == "test_config"
    assert module.requires_db is False
    assert module.enable_llm is False
    module._setup_logging.assert_called_once()
    module._load_config.assert_called_once()


def test_events_module_initialization_defaults(mocker: MagicMock) -> None:
    """Test the initialization of EventsModule with default values."""
    mocker.patch("dewey.core.crm.events.EventsModule._setup_logging")
    mocker.patch("dewey.core.crm.events.EventsModule._load_config")
    mocker.patch("dewey.core.crm.events.EventsModule._initialize_db_connection")
    mocker.patch("dewey.core.crm.events.EventsModule._initialize_llm_client")

    module = EventsModule()

    assert module.name == "EventsModule"
    assert module.description == "Manages CRM events."
    assert module.config_section == "events"
    assert module.requires_db is True
    assert module.enable_llm is False
    module._setup_logging.assert_called_once()
    module._load_config.assert_called_once()


def test_events_module_run_no_db_no_llm(events_module: EventsModule) -> None:
    """Test the run method when no database or LLM is enabled."""
    events_module.requires_db = False
    events_module.enable_llm = False
    events_module.run()

    events_module.logger.info.assert_called_with("Running EventsModule...")
    events_module.logger.debug.assert_called_with(
        "Config value for some_config_key: default_value"
    )
    events_module.logger.warning.assert_not_called()
    events_module.logger.error.assert_not_called()


def test_events_module_run_with_db(events_module: EventsModule) -> None:
    """Test the run method with a database connection."""
    events_module.requires_db = True
    events_module.enable_llm = False
    events_module.run()

    events_module.logger.info.assert_any_call("Running EventsModule...")
    events_module.logger.debug.assert_any_call(
        "Config value for some_config_key: default_value"
    )
    events_module.logger.info.assert_called_with("Successfully connected to the database.")
    events_module.logger.warning.assert_not_called()
    events_module.logger.error.assert_not_called()


def test_events_module_run_with_db_error(events_module: EventsModule) -> None:
    """Test the run method with a database connection error."""
    events_module.requires_db = True
    events_module.enable_llm = False
    events_module.db_conn.__enter__.side_effect = Exception("DB Error")
    events_module.run()

    events_module.logger.info.assert_any_call("Running EventsModule...")
    events_module.logger.debug.assert_any_call(
        "Config value for some_config_key: default_value"
    )
    events_module.logger.error.assert_called_with(
        "Error interacting with the database: DB Error"
    )
    events_module.logger.warning.assert_not_called()


def test_events_module_run_with_llm(events_module: EventsModule) -> None:
    """Test the run method with an LLM client."""
    events_module.requires_db = False
    events_module.enable_llm = True
    events_module.llm_client.generate_text.return_value = "LLM Summary"
    events_module.run()

    events_module.logger.info.assert_any_call("Running EventsModule...")
    events_module.logger.debug.assert_any_call(
        "Config value for some_config_key: default_value"
    )
    events_module.logger.info.assert_called_with("LLM Response: LLM Summary")
    events_module.logger.debug.assert_called_with("LLM client is not enabled.")
    events_module.logger.warning.assert_not_called()
    events_module.logger.error.assert_not_called()


def test_events_module_run_with_llm_error(events_module: EventsModule) -> None:
    """Test the run method with an LLM client error."""
    events_module.requires_db = False
    events_module.enable_llm = True
    events_module.llm_client.generate_text.side_effect = Exception("LLM Error")
    events_module.run()

    events_module.logger.info.assert_any_call("Running EventsModule...")
    events_module.logger.debug.assert_any_call(
        "Config value for some_config_key: default_value"
    )
    events_module.logger.error.assert_called_with("Error interacting with the LLM: LLM Error")
    events_module.logger.debug.assert_called_with("LLM client is not enabled.")
    events_module.logger.warning.assert_not_called()


def test_events_module_get_config_value(events_module: EventsModule) -> None:
    """Test the get_config_value method."""
    events_module.config = {"key1": "value1", "key2": {"nested_key": "nested_value"}}

    assert events_module.get_config_value("key1") == "value1"
    assert events_module.get_config_value("key2.nested_key") == "nested_value"
    assert events_module.get_config_value("key3", "default") == "default"
    assert events_module.get_config_value("key2.nonexistent_key", "default") == "default"


def test_events_module_setup_logging(mocker: MagicMock) -> None:
    """Test the _setup_logging method."""
    # Mock the config load and file open
    mocker.patch("dewey.core.crm.events.CONFIG_PATH", Path("/tmp/test_config.yaml"))
    mock_open = mocker.mock_open(
        read_data=yaml.dump(
            {
                "core": {
                    "logging": {
                        "level": "DEBUG",
                        "format": "%(levelname)s - %(message)s",
                        "date_format": "%Y-%m-%d",
                    }
                }
            }
        )
    )
    mocker.patch("builtins.open", mock_open)

    # Create an EventsModule instance
    module = EventsModule()

    # Assert that logging is configured correctly
    assert logging.getLogger().level == logging.DEBUG
    assert logging.getLogger().handlers[0].formatter._fmt == "%(levelname)s - %(message)s"  # type: ignore

    # Test when config file is not found
    mocker.patch("builtins.open", side_effect=FileNotFoundError)
    module = EventsModule()
    assert logging.getLogger().level == logging.INFO
    assert logging.getLogger().handlers[0].formatter._fmt == "%(asctime)s - %(levelname)s - %(name)s - %(message)s"  # type: ignore


def test_events_module_load_config(mocker: MagicMock) -> None:
    """Test the _load_config method."""
    # Mock the config load and file open
    mocker.patch("dewey.core.crm.events.CONFIG_PATH", Path("/tmp/test_config.yaml"))
    mock_open = mocker.mock_open(read_data=yaml.dump({"test_config": {"key": "value"}}))
    mocker.patch("builtins.open", mock_open)

    # Create an EventsModule instance
    module = EventsModule(config_section="test_config")

    # Assert that the config is loaded correctly
    assert module.config == {"key": "value"}

    # Test when config section is not found
    mock_open = mocker.mock_open(read_data=yaml.dump({"other_config": {"key": "value"}}))
    mocker.patch("builtins.open", mock_open)
    module = EventsModule(config_section="test_config")
    assert module.config == {"other_config": {"key": "value"}}

    # Test when config file is not found
    mocker.patch("builtins.open", side_effect=FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        module = EventsModule(config_section="test_config")
        module._load_config()

    # Test when config file is invalid YAML
    mocker.patch("builtins.open", side_effect=yaml.YAMLError)
    with pytest.raises(yaml.YAMLError):
        module = EventsModule(config_section="test_config")
        module._load_config()


def test_events_module_initialize_db_connection(mocker: MagicMock) -> None:
    """Test the _initialize_db_connection method."""
    # Mock the get_connection function
    mock_get_connection = mocker.patch("dewey.core.crm.events.get_connection")
    mock_db_conn = mocker.MagicMock()
    mock_get_connection.return_value = mock_db_conn

    # Create an EventsModule instance
    module = EventsModule(requires_db=True)
    module.config = {"core": {"database": {"db_url": "test_url"}}}
    module._initialize_db_connection()

    # Assert that the database connection is initialized correctly
    mock_get_connection.assert_called_once_with({"db_url": "test_url"})
    assert module.db_conn == mock_db_conn

    # Test when the database module cannot be imported
    mocker.patch("dewey.core.crm.events.get_connection", side_effect=ImportError)
    module = EventsModule(requires_db=True)
    with pytest.raises(ImportError):
        module._initialize_db_connection()

    # Test when the database connection fails
    mock_get_connection.side_effect = Exception("DB Connection Error")
    module = EventsModule(requires_db=True)
    with pytest.raises(Exception, match="Failed to initialize database connection"):
        module._initialize_db_connection()


def test_events_module_initialize_llm_client(mocker: MagicMock) -> None:
    """Test the _initialize_llm_client method."""
    # Mock the get_llm_client function
    mock_get_llm_client = mocker.patch("dewey.core.crm.events.get_llm_client")
    mock_llm_client = mocker.MagicMock()
    mock_get_llm_client.return_value = mock_llm_client

    # Create an EventsModule instance
    module = EventsModule(enable_llm=True)
    module.config = {"llm": {"model": "test_model"}}
    module._initialize_llm_client()

    # Assert that the LLM client is initialized correctly
    mock_get_llm_client.assert_called_once_with({"model": "test_model"})
    assert module.llm_client == mock_llm_client

    # Test when the LLM module cannot be imported
    mocker.patch("dewey.core.crm.events.get_llm_client", side_effect=ImportError)
    module = EventsModule(enable_llm=True)
    with pytest.raises(ImportError):
        module._initialize_llm_client()

    # Test when the LLM client initialization fails
    mock_get_llm_client.side_effect = Exception("LLM Client Error")
    module = EventsModule(enable_llm=True)
    with pytest.raises(Exception, match="Failed to initialize LLM client"):
        module._initialize_llm_client()


def test_events_module_setup_argparse(events_module: EventsModule) -> None:
    """Test the setup_argparse method."""
    parser = events_module.setup_argparse()
    assert parser.description == "Manages CRM events."
    assert parser._actions[1].dest == "config"
    assert parser._actions[2].dest == "log_level"


def test_events_module_parse_args(mocker: MagicMock, events_module: EventsModule) -> None:
    """Test the parse_args method."""
    # Mock the setup_argparse method
    mock_parser = mocker.MagicMock()
    mock_args = mocker.MagicMock()
    mock_parser.parse_args.return_value = mock_args
    events_module.setup_argparse = mocker.MagicMock(return_value=mock_parser)

    # Mock the logging and configuration
    events_module.logger = mocker.MagicMock()
    events_module.config = {}

    # Mock the database and LLM connections
    events_module.requires_db = True
    events_module.enable_llm = True
    mock_args.log_level = "DEBUG"
    mock_args.config = "/tmp/test_config.yaml"
    mock_args.db_connection_string = "test_db_string"
    mock_args.llm_model = "test_llm_model"

    # Mock the file open
    mock_open = mocker.mock_open(read_data=yaml.dump({"key": "value"}))
    mocker.patch("builtins.open", mock_open)

    # Call the parse_args method
    args = events_module.parse_args()

    # Assert that the arguments are parsed correctly
    events_module.setup_argparse.assert_called_once()
    mock_parser.parse_args.assert_called_once()
    assert args == mock_args

    # Assert that the log level is updated
    events_module.logger.setLevel.assert_called_with(logging.DEBUG)
    events_module.logger.debug.assert_called_with("Log level set to DEBUG")

    # Assert that the config is loaded
    assert events_module.config == {"key": "value"}
    events_module.logger.info.assert_called_with("Loaded configuration from /tmp/test_config.yaml")

    # Assert that the database connection is updated
    from dewey.core.db.connection import get_connection

    get_connection = mocker.patch("dewey.core.crm.events.get_connection")
    events_module.db_conn = get_connection({"connection_string": "test_db_string"})
    events_module.logger.info.assert_called_with("Using custom database connection")

    # Assert that the LLM model is updated
    from dewey.llm.llm_utils import get_llm_client

    get_llm_client = mocker.patch("dewey.core.crm.events.get_llm_client")
    events_module.llm_client = get_llm_client({"model": "test_llm_model"})
    events_module.logger.info.assert_called_with("Using custom LLM model: test_llm_model")


def test_events_module_execute(mocker: MagicMock, events_module: EventsModule) -> None:
    """Test the execute method."""
    # Mock the parse_args and run methods
    mock_args = mocker.MagicMock()
    events_module.parse_args = mocker.MagicMock(return_value=mock_args)
    events_module.run = mocker.MagicMock()
    events_module._cleanup = mocker.MagicMock()

    # Call the execute method
    events_module.execute()

    # Assert that the methods are called correctly
    events_module.parse_args.assert_called_once()
    events_module.logger.info.assert_any_call("Starting execution of EventsModule")
    events_module.run.assert_called_once()
    events_module.logger.info.assert_any_call("Completed execution of EventsModule")
    events_module._cleanup.assert_called_once()

    # Test when a KeyboardInterrupt is raised
    events_module.parse_args.return_value = mock_args
    events_module.run.side_effect = KeyboardInterrupt
    with pytest.raises(SystemExit) as excinfo:
        events_module.execute()
    assert excinfo.value.code == 1
    events_module.logger.warning.assert_called_with("Script interrupted by user")
    events_module._cleanup.assert_called_once()

    # Test when an Exception is raised
    events_module.parse_args.return_value = mock_args
    events_module.run.side_effect = Exception("Test Exception")
    with pytest.raises(SystemExit) as excinfo:
        events_module.execute()
    assert excinfo.value.code == 1
    events_module.logger.error.assert_called_with(
        "Error executing script: Test Exception", exc_info=True
    )
    events_module._cleanup.assert_called_once()


def test_events_module_cleanup(mocker: MagicMock, events_module: EventsModule) -> None:
    """Test the _cleanup method."""
    # Mock the database connection
    events_module.db_conn = mocker.MagicMock()
    events_module.logger = mocker.MagicMock()

    # Call the _cleanup method
    events_module._cleanup()

    # Assert that the database connection is closed
    events_module.logger.debug.assert_called_with("Closing database connection")
    events_module.db_conn.close.assert_called_once()

    # Test when the database connection is None
    events_module.db_conn = None
    events_module._cleanup()
    events_module.logger.debug.assert_called_with("Closing database connection")

    # Test when the database connection fails to close
    events_module.db_conn = mocker.MagicMock()
    events_module.db_conn.close.side_effect = Exception("Close Error")
    events_module._cleanup()
    events_module.logger.warning.assert_called_with("Error closing database connection: Close Error")


def test_events_module_get_path(events_module: EventsModule) -> None:
    """Test the get_path method."""
    # Test with a relative path
    relative_path = "test_file.txt"
    expected_path = Path("/Users/srvo/dewey") / relative_path
    assert events_module.get_path(relative_path) == expected_path

    # Test with an absolute path
    absolute_path = "/tmp/test_file.txt"
    assert events_module.get_path(absolute_path) == Path(absolute_path)

