import pytest
from unittest.mock import MagicMock
from dewey.core.analysis.validation import Validation
from dewey.core.base_script import BaseScript
import logging


# Mock the BaseScript class and its methods
@pytest.fixture
def mock_base_script(mocker):
    """Mocks the BaseScript class."""
    mock = mocker.MagicMock(spec=BaseScript)
    mock.logger = mocker.MagicMock(spec=logging.Logger)
    mock.config = {}
    mock.db_conn = None
    mock.llm_client = None
    mock.get_config_value.return_value = "default_value"
    return mock


@pytest.fixture
def validation_instance(mock_base_script, mocker):
    """Creates a Validation instance with mocked dependencies."""
    mocker.patch(
        "dewey.core.analysis.validation.BaseScript.__init__", return_value=None
    )
    validation = Validation()
    validation.logger = mock_base_script.logger
    validation.config = mock_base_script.config
    validation.db_conn = mock_base_script.db_conn
    validation.llm_client = mock_base_script.llm_client
    validation.get_config_value = mock_base_script.get_config_value
    return validation


def test_validation_initialization(mocker):
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


def test_run_method(validation_instance):
    """Tests the run method of the Validation class."""
    validation_instance.run()
    validation_instance.logger.info.assert_called()
    validation_instance.get_config_value.assert_called_with(
        "example_config_key", "default_value"
    )


@pytest.mark.parametrize(
    "data, llm_response, expected_result, log_level",
    [
        ({"key": "value"}, "Valid", True, "INFO"),
        (
            {"key": "value"},
            "Invalid",
            True,
            "INFO",
        ),  # LLM response doesn't affect return
        ("not a dict", "Valid", False, "ERROR"),
        ({"key": "value"}, Exception("LLM Error"), False, "ERROR"),
    ],
)
def test_example_method(
    validation_instance, data, llm_response, expected_result, log_level
):
    """Tests the example_method with various inputs and LLM responses."""
    # Mock the LLM call
    if isinstance(llm_response, Exception):
        validation_instance.llm_client = MagicMock()
        validation_instance.llm_client.chat.completions.create.side_effect = (
            llm_response
        )
    else:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=llm_response))]
        validation_instance.llm_client = MagicMock()
        validation_instance.llm_client.chat.completions.create.return_value = (
            mock_response
        )

    # Mock the database call
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [1]
    mock_db_conn = MagicMock()
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
    validation_instance.db_conn = mock_db_conn

    if data == "not a dict":
        result = validation_instance.example_method(data)
        assert result == expected_result
        validation_instance.logger.error.assert_called_with("Data is not a dictionary.")
    elif isinstance(llm_response, Exception):
        result = validation_instance.example_method(data)
        assert result == expected_result
        validation_instance.logger.exception.assert_called()
    else:
        result = validation_instance.example_method(data)
        assert result == expected_result
        validation_instance.llm_client.chat.completions.create.assert_called()
        mock_db_conn.cursor.assert_called()
        mock_cursor.execute.assert_called_with("SELECT 1;")
        mock_cursor.fetchone.assert_called()
        validation_instance.logger.info.assert_called()


def test_example_method_no_llm(validation_instance, mocker):
    """Tests the example_method when LLM is disabled."""
    validation_instance.enable_llm = False
    validation_instance.llm_client = None

    data = {"key": "value"}

    # Mock the database call
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [1]
    mock_db_conn = MagicMock()
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
    validation_instance.db_conn = mock_db_conn

    result = validation_instance.example_method(data)
    assert result == True
    mock_db_conn.cursor.assert_called()
    mock_cursor.execute.assert_called_with("SELECT 1;")
    mock_cursor.fetchone.assert_called()
    validation_instance.logger.info.assert_called()


def test_example_method_no_db(validation_instance, mocker):
    """Tests the example_method when DB is disabled."""
    validation_instance.requires_db = False
    validation_instance.db_conn = None
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Valid"))]
    validation_instance.llm_client = MagicMock()
    validation_instance.llm_client.chat.completions.create.return_value = mock_response
    data = {"key": "value"}
    result = validation_instance.example_method(data)
    assert result == True
    validation_instance.llm_client.chat.completions.create.assert_called()
    validation_instance.logger.info.assert_called()


def test_execute_method(validation_instance, mocker):
    """Tests the execute method of the Validation class."""
    mock_parse_args = mocker.patch.object(Validation, "parse_args")
    mock_run = mocker.patch.object(Validation, "run")
    mock_cleanup = mocker.patch.object(Validation, "_cleanup")

    mock_args = MagicMock()
    mock_parse_args.return_value = mock_args

    validation_instance.execute()

    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()
    validation_instance.logger.info.assert_called()


def test_execute_method_keyboard_interrupt(validation_instance, mocker):
    """Tests the execute method with a KeyboardInterrupt."""
    mock_parse_args = mocker.patch.object(Validation, "parse_args")
    mock_run = mocker.patch.object(Validation, "run", side_effect=KeyboardInterrupt)
    mock_cleanup = mocker.patch.object(Validation, "_cleanup")
    mock_exit = mocker.patch("sys.exit")

    mock_args = MagicMock()
    mock_parse_args.return_value = mock_args

    validation_instance.execute()

    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()
    mock_exit.assert_called_with(1)
    validation_instance.logger.warning.assert_called_with("Script interrupted by user")


def test_execute_method_exception(validation_instance, mocker):
    """Tests the execute method with an exception."""
    mock_parse_args = mocker.patch.object(Validation, "parse_args")
    mock_run = mocker.patch.object(
        Validation, "run", side_effect=ValueError("Test Exception")
    )
    mock_cleanup = mocker.patch.object(Validation, "_cleanup")
    mock_exit = mocker.patch("sys.exit")

    mock_args = MagicMock()
    mock_parse_args.return_value = mock_args

    validation_instance.execute()

    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()
    mock_exit.assert_called_with(1)
    validation_instance.logger.error.assert_called()


def test_cleanup_method(validation_instance):
    """Tests the _cleanup method of the Validation class."""
    mock_db_conn = MagicMock()
    validation_instance.db_conn = mock_db_conn

    validation_instance._cleanup()

    mock_db_conn.close.assert_called_once()
    validation_instance.logger.debug.assert_called_with("Closing database connection")


def test_cleanup_method_no_db(validation_instance):
    """Tests the _cleanup method when there is no database connection."""
    validation_instance.db_conn = None
    validation_instance._cleanup()
    assert not validation_instance.logger.debug.called


def test_cleanup_method_exception(validation_instance):
    """Tests the _cleanup method when closing the database connection raises an exception."""
    mock_db_conn = MagicMock()
    mock_db_conn.close.side_effect = Exception("Test Exception")
    validation_instance.db_conn = mock_db_conn

    validation_instance._cleanup()

    mock_db_conn.close.assert_called_once()
    validation_instance.logger.warning.assert_called()


def test_get_path(validation_instance):
    """Tests the get_path method."""
    # Test with relative path
    relative_path = "test_file.txt"
    expected_path = validation_instance.PROJECT_ROOT / relative_path
    assert validation_instance.get_path(relative_path) == expected_path

    # Test with absolute path
    absolute_path = "/tmp/test_file.txt"
    assert validation_instance.get_path(absolute_path) == Path(absolute_path)


def test_get_config_value(validation_instance):
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


def test_setup_logging(validation_instance, mocker):
    """Tests the _setup_logging method."""
    mocker.patch("logging.basicConfig")
    validation_instance._setup_logging()
    logging.basicConfig.assert_called()
    assert isinstance(validation_instance.logger, logging.Logger)


def test_load_config(validation_instance, mocker):
    """Tests the _load_config method."""
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="test: value"))
    mocker.patch("yaml.safe_load", return_value={"test": "value"})

    config = validation_instance._load_config()

    mock_open.assert_called_with(validation_instance.CONFIG_PATH, "r")
    yaml.safe_load.assert_called()
    assert config == {"test": "value"}


def test_load_config_section(validation_instance, mocker):
    """Tests the _load_config method with a config section."""
    validation_instance.config_section = "test_section"
    mock_open = mocker.patch(
        "builtins.open", mocker.mock_open(read_data="test_section: {key: value}")
    )
    mocker.patch("yaml.safe_load", return_value={"test_section": {"key": "value"}})

    config = validation_instance._load_config()

    mock_open.assert_called_with(validation_instance.CONFIG_PATH, "r")
    yaml.safe_load.assert_called()
    assert config == {"key": "value"}


def test_load_config_section_missing(validation_instance, mocker):
    """Tests the _load_config method with a missing config section."""
    validation_instance.config_section = "missing_section"
    mock_open = mocker.patch(
        "builtins.open", mocker.mock_open(read_data="test_section: {key: value}")
    )
    mocker.patch("yaml.safe_load", return_value={"test_section": {"key": "value"}})

    config = validation_instance._load_config()

    mock_open.assert_called_with(validation_instance.CONFIG_PATH, "r")
    yaml.safe_load.assert_called()
    assert config == {"test_section": {"key": "value"}}
    validation_instance.logger.warning.assert_called()


def test_load_config_file_not_found(validation_instance, mocker):
    """Tests the _load_config method when the config file is not found."""
    mocker.patch("builtins.open", side_effect=FileNotFoundError)

    with pytest.raises(FileNotFoundError):
        validation_instance._load_config()
    validation_instance.logger.error.assert_called()


def test_load_config_yaml_error(validation_instance, mocker):
    """Tests the _load_config method when there is a YAML error."""
    mocker.patch("builtins.open", mocker.mock_open(read_data="invalid yaml"))
    mocker.patch("yaml.safe_load", side_effect=yaml.YAMLError)

    with pytest.raises(yaml.YAMLError):
        validation_instance._load_config()
    validation_instance.logger.error.assert_called()


def test_initialize_db_connection(validation_instance, mocker):
    """Tests the _initialize_db_connection method."""
    mock_get_connection = mocker.patch("dewey.core.analysis.validation.get_connection")
    validation_instance.config = {"core": {"database": {"test": "value"}}}

    validation_instance._initialize_db_connection()

    mock_get_connection.assert_called_with({"test": "value"})
    assert validation_instance.db_conn == mock_get_connection.return_value
    validation_instance.logger.debug.assert_called()


def test_initialize_db_connection_import_error(validation_instance, mocker):
    """Tests the _initialize_db_connection method when the database module cannot be imported."""
    mocker.patch(
        "dewey.core.analysis.validation.get_connection", side_effect=ImportError
    )

    with pytest.raises(ImportError):
        validation_instance._initialize_db_connection()
    validation_instance.logger.error.assert_called()


def test_initialize_db_connection_exception(validation_instance, mocker):
    """Tests the _initialize_db_connection method when there is an exception during initialization."""
    mocker.patch(
        "dewey.core.analysis.validation.get_connection",
        side_effect=Exception("Test Exception"),
    )
    validation_instance.config = {"core": {"database": {"test": "value"}}}

    with pytest.raises(Exception):
        validation_instance._initialize_db_connection()
    validation_instance.logger.error.assert_called()


def test_initialize_llm_client(validation_instance, mocker):
    """Tests the _initialize_llm_client method."""
    mock_get_llm_client = mocker.patch("dewey.core.analysis.validation.get_llm_client")
    validation_instance.config = {"llm": {"test": "value"}}

    validation_instance._initialize_llm_client()

    mock_get_llm_client.assert_called_with({"test": "value"})
    assert validation_instance.llm_client == mock_get_llm_client.return_value
    validation_instance.logger.debug.assert_called()


def test_initialize_llm_client_import_error(validation_instance, mocker):
    """Tests the _initialize_llm_client method when the LLM module cannot be imported."""
    mocker.patch(
        "dewey.core.analysis.validation.get_llm_client", side_effect=ImportError
    )

    with pytest.raises(ImportError):
        validation_instance._initialize_llm_client()
    validation_instance.logger.error.assert_called()


def test_initialize_llm_client_exception(validation_instance, mocker):
    """Tests the _initialize_llm_client method when there is an exception during initialization."""
    mocker.patch(
        "dewey.core.analysis.validation.get_llm_client",
        side_effect=Exception("Test Exception"),
    )
    validation_instance.config = {"llm": {"test": "value"}}

    with pytest.raises(Exception):
        validation_instance._initialize_llm_client()
    validation_instance.logger.error.assert_called()


def test_setup_argparse(validation_instance):
    """Tests the setup_argparse method."""
    parser = validation_instance.setup_argparse()
    assert parser.description == validation_instance.description
    assert parser.format_help()


def test_parse_args(validation_instance, mocker):
    """Tests the parse_args method."""
    mock_setup_argparse = mocker.patch.object(Validation, "setup_argparse")
    mock_parser = MagicMock()
    mock_setup_argparse.return_value = mock_parser
    mock_args = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_args.log_level = "DEBUG"
    mock_args.config = "test_config.yaml"
    mock_args.db_connection_string = "test_db_connection_string"
    mock_args.llm_model = "test_llm_model"
    mocker.patch("builtins.open", mocker.mock_open(read_data="test: value"))
    mocker.patch("yaml.safe_load", return_value={"test": "value"})
    mocker.patch("dewey.core.analysis.validation.get_connection")
    mocker.patch("dewey.core.analysis.validation.get_llm_client")
    mocker.patch.object(logging.Logger, "setLevel")

    args = validation_instance.parse_args()

    mock_setup_argparse.assert_called_once()
    mock_parser.parse_args.assert_called_once()
    assert args == mock_args
    logging.Logger.setLevel.assert_called_with(logging.DEBUG)
    validation_instance.logger.debug.assert_called()
    validation_instance.logger.info.assert_called()


def test_parse_args_no_args(validation_instance, mocker):
    """Tests the parse_args method with no arguments."""
    mock_setup_argparse = mocker.patch.object(Validation, "setup_argparse")
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
