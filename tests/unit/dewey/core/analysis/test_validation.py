"""Tests for dewey.core.analysis.validation."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.analysis.validation import Validation, LLMClientInterface, DatabaseConnectionInterface
from dewey.core.db.connection import DatabaseConnection
from dewey.llm import llm_utils


@pytest.fixture
def mock_base_script(mocker: Any) -> MagicMock:
    """Mocks the BaseScript class."""
    mock = mocker.MagicMock(spec=BaseScript)
    mock.logger = mocker.MagicMock(spec=logging.Logger)
    mock.config = {}
    mock.db_conn = None
    mock.llm_client = None
    mock.get_config_value.return_value = "default_value"
    mock.PROJECT_ROOT = Path("/Users/srvo/dewey")  # Set the project root
    mock.CONFIG_PATH = mock.PROJECT_ROOT / "config" / "dewey.yaml"
    return mock


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mocks the LLMClientInterface."""
    return MagicMock(spec=LLMClientInterface)


@pytest.fixture
def mock_db_conn() -> MagicMock:
    """Mocks the DatabaseConnectionInterface."""
    return MagicMock(spec=DatabaseConnectionInterface)


@pytest.fixture
def validation_instance(mock_base_script: MagicMock, mock_llm_client: MagicMock, mock_db_conn: MagicMock, mocker: Any) -> Validation:
    """Creates a Validation instance with mocked dependencies."""
    mocker.patch(
        "dewey.core.analysis.validation.BaseScript.__init__", return_value=None
    )
    validation = Validation(llm_client=mock_llm_client, db_conn=mock_db_conn)
    validation.logger = mock_base_script.logger
    validation.config = mock_base_script.config
    validation.get_config_value = mock_base_script.get_config_value
    validation.PROJECT_ROOT = mock_base_script.PROJECT_ROOT
    validation.CONFIG_PATH = mock_base_script.CONFIG_PATH
    return validation


def test_validation_initialization(mocker: Any) -> None:
    """Tests the initialization of the Validation class."""
    mocker.patch(
        "dewey.core.analysis.validation.BaseScript.__init__", return_value=None
    )
    validation = Validation()
    assert validation.config_section == "validation"
    # Verify that BaseScript's __init__ was called with the correct arguments
    dewey.core.analysis.validation.BaseScript.__init__.assert_called_once_with(
        config_section="validation", requires_db=True, enable_llm=True
    )


def test_validation_initialization_with_mocks(mocker: Any, mock_llm_client: MagicMock, mock_db_conn: MagicMock) -> None:
    """Tests the initialization of the Validation class with injected mocks."""
    mocker.patch(
        "dewey.core.analysis.validation.BaseScript.__init__", return_value=None
    )
    validation = Validation(llm_client=mock_llm_client, db_conn=mock_db_conn)
    assert validation.llm_client == mock_llm_client
    assert validation.db_conn == mock_db_conn


def test_llm_client_property(validation_instance: Validation, mock_llm_client: MagicMock) -> None:
    """Tests the llm_client property."""
    assert validation_instance.llm_client == mock_llm_client
    new_llm_client = MagicMock(spec=LLMClientInterface)
    validation_instance.llm_client = new_llm_client
    assert validation_instance.llm_client == new_llm_client


def test_db_conn_property(validation_instance: Validation, mock_db_conn: MagicMock) -> None:
    """Tests the db_conn property."""
    assert validation_instance.db_conn == mock_db_conn
    new_db_conn = MagicMock(spec=DatabaseConnectionInterface)
    validation_instance.db_conn = new_db_conn
    assert validation_instance.db_conn == new_db_conn


@patch("dewey.core.analysis.validation.BaseScript.get_config_value")
@patch("dewey.core.analysis.validation.Validation.example_method")
def test_run_method(
    mock_example_method: MagicMock,
    mock_get_config_value: MagicMock,
    validation_instance: Validation,
) -> None:
    """Tests the run method of the Validation class."""
    mock_get_config_value.return_value = "test_value"
    validation_instance.run()
    validation_instance.logger.info.assert_called()
    mock_get_config_value.assert_called_with("utils.example_config", "default_value")
    mock_example_method.assert_called_with({"example": "data"})


@pytest.mark.parametrize(
    "data, llm_response, db_result, expected_result",
    [
        ({"key": "value"}, "Valid", [1], True),
        ({"key": "value"}, "Invalid", [1], True),
        ({"key": "value"}, None, [1], True),
        ({"key": "value"}, "Valid", None, True),
        ({"key": "value"}, None, None, True),
    ],
)
def test_example_method(
    validation_instance: Validation,
    mock_llm_client: MagicMock,
    mock_db_conn: MagicMock,
    data: Dict[str, Any],
    llm_response: Optional[str],
    db_result: Optional[List[Any]],
    expected_result: bool,
) -> None:
    """Tests the example_method with various inputs and LLM responses."""
    # Arrange
    mock_llm_client.call_llm.return_value = llm_response
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = db_result
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Act
    result = validation_instance.example_method(data)

    # Assert
    assert result == expected_result
    if validation_instance.llm_client:
        mock_llm_client.call_llm.assert_called_once_with("Is this data valid?", data)
        validation_instance.logger.info.assert_called()
    if validation_instance.db_conn:
        mock_db_conn.cursor.assert_called()
        mock_cursor.execute.assert_called_with("SELECT 1;")
        mock_cursor.fetchone.assert_called()
        validation_instance.logger.info.assert_called()


def test_example_method_value_error(validation_instance: Validation) -> None:
    """Tests the example_method raises ValueError when data is not a dict."""
    data = "not a dict"
    with pytest.raises(ValueError, match="Data must be a dictionary."):
        validation_instance.example_method(data)
    validation_instance.logger.error.assert_called_with("Data is not a dictionary.")


def test_example_method_exception(validation_instance: Validation, mock_llm_client: MagicMock, mock_db_conn: MagicMock) -> None:
    """Tests the example_method handles exceptions during LLM or DB calls."""
    mock_llm_client.call_llm.side_effect = Exception("LLM Error")
    data = {"key": "value"}
    result = validation_instance.example_method(data)
    assert result is False
    validation_instance.logger.exception.assert_called()


def test_example_method_no_llm(
    validation_instance: Validation, mocker: Any, mock_db_conn: MagicMock
) -> None:
    """Tests the example_method when LLM is disabled."""
    validation_instance._llm_client = None

    data = {"key": "value"}

    # Mock the database call
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [1]
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor

    result = validation_instance.example_method(data)
    assert result == True
    mock_db_conn.cursor.assert_called()
    mock_cursor.execute.assert_called_with("SELECT 1;")
    mock_cursor.fetchone.assert_called()
    validation_instance.logger.info.assert_called()


def test_example_method_no_db(
    validation_instance: Validation, mocker: Any, mock_llm_client: MagicMock
) -> None:
    """Tests the example_method when DB is disabled."""
    validation_instance._db_conn = None
    mock_llm_client.call_llm.return_value = "Valid"
    data = {"key": "value"}
    result = validation_instance.example_method(data)
    assert result == True
    mock_llm_client.call_llm.assert_called()
    validation_instance.logger.info.assert_called()


@patch("dewey.core.analysis.validation.Validation.parse_args")
@patch("dewey.core.analysis.validation.Validation.run")
@patch("dewey.core.analysis.validation.Validation._cleanup")
def test_execute_method(
    mock_cleanup: MagicMock,
    mock_run: MagicMock,
    mock_parse_args: MagicMock,
    validation_instance: Validation,
) -> None:
    """Tests the execute method of the Validation class."""
    mock_args = MagicMock()
    mock_parse_args.return_value = mock_args

    validation_instance.execute()

    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()
    validation_instance.logger.info.assert_called()


@patch("dewey.core.analysis.validation.Validation.parse_args")
@patch("dewey.core.analysis.validation.Validation.run", side_effect=KeyboardInterrupt)
@patch("dewey.core.analysis.validation.Validation._cleanup")
@patch("sys.exit")
def test_execute_method_keyboard_interrupt(
    mock_exit: MagicMock,
    mock_cleanup: MagicMock,
    mock_run: MagicMock,
    mock_parse_args: MagicMock,
    validation_instance: Validation,
) -> None:
    """Tests the execute method with a KeyboardInterrupt."""
    mock_args = MagicMock()
    mock_parse_args.return_value = mock_args

    validation_instance.execute()

    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()
    mock_exit.assert_called_with(1)
    validation_instance.logger.warning.assert_called_with("Script interrupted by user")


@patch("dewey.core.analysis.validation.Validation.parse_args")
@patch("dewey.core.analysis.validation.Validation.run", side_effect=ValueError("Test Exception"))
@patch("dewey.core.analysis.validation.Validation._cleanup")
@patch("sys.exit")
def test_execute_method_exception(
    mock_exit: MagicMock,
    mock_cleanup: MagicMock,
    mock_run: MagicMock,
    mock_parse_args: MagicMock,
    validation_instance: Validation,
) -> None:
    """Tests the execute method with an exception."""
    mock_args = MagicMock()
    mock_parse_args.return_value = mock_args

    validation_instance.execute()

    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()
    mock_exit.assert_called_with(1)
    validation_instance.logger.error.assert_called()


def test_cleanup_method(validation_instance: Validation, mock_db_conn: MagicMock) -> None:
    """Tests the _cleanup method of the Validation class."""
    validation_instance._db_conn = mock_db_conn

    validation_instance._cleanup()

    mock_db_conn.close.assert_called_once()
    validation_instance.logger.debug.assert_called_with("Closing database connection")


def test_cleanup_method_no_db(validation_instance: Validation) -> None:
    """Tests the _cleanup method when there is no database connection."""
    validation_instance._db_conn = None
    validation_instance._cleanup()
    assert not validation_instance.logger.debug.called


def test_cleanup_method_exception(validation_instance: Validation, mock_db_conn: MagicMock) -> None:
    """Tests the _cleanup method when closing the database connection raises an exception."""
    mock_db_conn.close.side_effect = Exception("Test Exception")
    validation_instance._db_conn = mock_db_conn

    validation_instance._cleanup()

    mock_db_conn.close.assert_called_once()
    validation_instance.logger.warning.assert_called()


def test_get_path(validation_instance: Validation) -> None:
    """Tests the get_path method."""
    # Test with relative path
    relative_path = "test_file.txt"
    expected_path = validation_instance.PROJECT_ROOT / relative_path
    assert validation_instance.get_path(relative_path) == expected_path

    # Test with absolute path
    absolute_path = "/tmp/test_file.txt"
    assert validation_instance.get_path(absolute_path) == Path(absolute_path)


def test_get_config_value(validation_instance: Validation) -> None:
    """Tests the get_config_value method."""
    validation_instance.config = {"level1": {"level2": {"key": "value"}}}

    # Test with valid key
    assert validation_instance.get_config_value("level1.level2.key") == "value"

    # Test with invalid key and default value
    assert (
        validation_instance.get_config_value("level1.level2.invalid_key", "default")
        == "default"
    )

    # Test with invalid key and no default value
    assert validation_instance.get_config_value("level1.level2.invalid_key") is None

    # Test with missing level
    assert (
        validation_instance.get_config_value("level1.invalid_level.key", "default")
        == "default"
    )


@patch("logging.basicConfig")
def test_setup_logging(mock_basicConfig: MagicMock, validation_instance: Validation) -> None:
    """Tests the _setup_logging method."""
    validation_instance._setup_logging()
    mock_basicConfig.assert_called()
    assert isinstance(validation_instance.logger, logging.Logger)


@patch("yaml.safe_load")
@patch("builtins.open", new_callable=mock_open, read_data="test: value")
def test_load_config(
    mock_open_file: MagicMock, mock_safe_load: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _load_config method."""
    mock_safe_load.return_value = {"test": "value"}

    config = validation_instance._load_config()

    mock_open_file.assert_called_with(validation_instance.CONFIG_PATH, "r")
    mock_safe_load.assert_called()
    assert config == {"test": "value"}


@patch("yaml.safe_load")
@patch(
    "builtins.open", new_callable=mock_open, read_data="test_section: {key: value}"
)
def test_load_config_section(
    mock_open_file: MagicMock, mock_safe_load: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _load_config method with a config section."""
    validation_instance.config_section = "test_section"
    mock_safe_load.return_value = {"test_section": {"key": "value"}}

    config = validation_instance._load_config()

    mock_open_file.assert_called_with(validation_instance.CONFIG_PATH, "r")
    mock_safe_load.assert_called()
    assert config == {"key": "value"}


@patch("yaml.safe_load")
@patch(
    "builtins.open", new_callable=mock_open, read_data="test_section: {key: value}"
)
def test_load_config_section_missing(
    mock_open_file: MagicMock, mock_safe_load: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _load_config method with a missing config section."""
    validation_instance.config_section = "missing_section"
    mock_safe_load.return_value = {"test_section": {"key": "value"}}
    validation_instance.logger = MagicMock()

    config = validation_instance._load_config()

    mock_open_file.assert_called_with(validation_instance.CONFIG_PATH, "r")
    mock_safe_load.assert_called()
    assert config == {"test_section": {"key": "value"}}
    validation_instance.logger.warning.assert_called()


@patch("builtins.open", side_effect=FileNotFoundError)
def test_load_config_file_not_found(
    mock_open_file: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _load_config method when the config file is not found."""
    validation_instance.logger = MagicMock()

    with pytest.raises(FileNotFoundError):
        validation_instance._load_config()
    validation_instance.logger.error.assert_called()


@patch("yaml.safe_load", side_effect=yaml.YAMLError)
@patch("builtins.open", new_callable=mock_open, read_data="invalid yaml")
def test_load_config_yaml_error(
    mock_open_file: MagicMock, mock_safe_load: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _load_config method when there is a YAML error."""
    validation_instance.logger = MagicMock()

    with pytest.raises(yaml.YAMLError):
        validation_instance._load_config()
    validation_instance.logger.error.assert_called()


@patch("dewey.core.analysis.validation.get_connection")
def test_initialize_db_connection(
    mock_get_connection: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _initialize_db_connection method."""
    validation_instance.config = {"database": {"test": "value"}}
    validation_instance.db_conn = None

    validation_instance._initialize_db_connection()

    mock_get_connection.assert_called_with({"test": "value"})
    assert validation_instance.db_conn is not None
    validation_instance.logger.debug.assert_called()


@patch("dewey.core.analysis.validation.get_connection", side_effect=ImportError)
def test_initialize_db_connection_import_error(
    mock_get_connection: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _initialize_db_connection method when the database module cannot be imported."""
    validation_instance.logger = MagicMock()
    validation_instance.db_conn = None

    with pytest.raises(ImportError):
        validation_instance._initialize_db_connection()
    validation_instance.logger.error.assert_called()


@patch(
    "dewey.core.analysis.validation.get_connection",
    side_effect=Exception("Test Exception"),
)
def test_initialize_db_connection_exception(
    mock_get_connection: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _initialize_db_connection method when there is an exception during initialization."""
    validation_instance.config = {"database": {"test": "value"}}
    validation_instance.logger = MagicMock()
    validation_instance.db_conn = None

    with pytest.raises(Exception):
        validation_instance._initialize_db_connection()
    validation_instance.logger.error.assert_called()


@patch("dewey.llm.llm_utils.get_llm_client")
def test_initialize_llm_client(
    mock_get_llm_client: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _initialize_llm_client method."""
    validation_instance.config = {"llm": {"test": "value"}}
    validation_instance.llm_client = None

    validation_instance._initialize_llm_client()

    mock_get_llm_client.assert_called_with({"test": "value"})
    assert validation_instance.llm_client is not None
    validation_instance.logger.debug.assert_called()


@patch("dewey.llm.llm_utils.get_llm_client", side_effect=ImportError)
def test_initialize_llm_client_import_error(
    mock_get_llm_client: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _initialize_llm_client method when the LLM module cannot be imported."""
    validation_instance.logger = MagicMock()
    validation_instance.llm_client = None

    with pytest.raises(ImportError):
        validation_instance._initialize_llm_client()
    validation_instance.logger.error.assert_called()


@patch(
    "dewey.llm.llm_utils.get_llm_client", side_effect=Exception("Test Exception")
)
def test_initialize_llm_client_exception(
    mock_get_llm_client: MagicMock, validation_instance: Validation
) -> None:
    """Tests the _initialize_llm_client method when there is an exception during initialization."""
    validation_instance.config = {"llm": {"test": "value"}}
    validation_instance.logger = MagicMock()
    validation_instance.llm_client = None

    with pytest.raises(Exception):
        validation_instance._initialize_llm_client()
    validation_instance.logger.error.assert_called()


def test_setup_argparse(validation_instance: Validation) -> None:
    """Tests the setup_argparse method."""
    parser = validation_instance.setup_argparse()
    assert parser.description == validation_instance.description
    assert parser.format_help()


@patch("dewey.core.analysis.validation.Validation.setup_argparse")
@patch("builtins.open", new_callable=mock_open, read_data="test: value")
@patch("yaml.safe_load", return_value={"test": "value"})
@patch("dewey.core.db.connection.get_connection")
@patch("dewey.llm.llm_utils.get_llm_client")
@patch.object(logging.Logger, "setLevel")
def test_parse_args(
    mock_set_level: MagicMock,
    mock_get_llm_client: MagicMock,
    mock_get_connection: MagicMock,
    mock_safe_load: MagicMock,
    mock_open_file: MagicMock,
    mock_setup_argparse: MagicMock,
    validation_instance: Validation,
) -> None:
    """Tests the parse_args method."""
    mock_parser = MagicMock()
    mock_setup_argparse.return_value = mock_parser
    mock_args = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_args.log_level = "DEBUG"
    mock_args.config = "test_config.yaml"
    mock_args.db_connection_string = "test_db_connection_string"
    mock_args.llm_model = "test_llm_model"

    args = validation_instance.parse_args()

    mock_setup_argparse.assert_called_once()
    mock_parser.parse_args.assert_called_once()
    assert args == mock_args
    mock_set_level.assert_called_with(logging.DEBUG)
    validation_instance.logger.debug.assert_called()
    validation_instance.logger.info.assert_called()


@patch("dewey.core.analysis.validation.Validation.setup_argparse")
def test_parse_args_no_args(
    mock_setup_argparse: MagicMock, validation_instance: Validation
) -> None:
    """Tests the parse_args method with no arguments."""
    mock_parser = MagicMock()
    mock_setup_argparse.return_value = mock_parser
    mock_args = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_args.log_level = None
    mock_args.config = None
    mock_args.db_connection_string = None
    mock_args.llm_model = None

    args = validation_instance.parse_args()

    mock_setup_argparse.assert_called_once()
    mock_parser.parse_args.assert_called_once()
    assert args == mock_args
