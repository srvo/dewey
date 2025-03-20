import csv
import io
import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.crm.data_ingestion.csv_schema_infer import CSVInferSchema
from dewey.core.db.connection import DatabaseConnection


@pytest.fixture
def csv_data() -> str:
    """Fixture providing sample CSV data."""
    return "header1,header2\nvalue1,value2\nvalue3,value4"


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture providing a mock configuration."""
    return {
        "csv_file_path": "test.csv",
        "table_name": "test_table",
        "core": {"database": {}},
        "llm": {},
    }


@pytest.fixture
def csv_infer_schema(mock_config: Dict[str, Any]) -> CSVInferSchema:
    """Fixture providing a CSVInferSchema instance with mocked config."""
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.CONFIG_PATH", new=MagicMock()):
        csv_infer = CSVInferSchema()
        csv_infer.config = mock_config
        csv_infer.logger = MagicMock()
        csv_infer.db_conn = MagicMock()
        csv_infer.llm_client = MagicMock()
        return csv_infer


def test_csv_infer_schema_initialization(csv_infer_schema: CSVInferSchema) -> None:
    """Test CSVInferSchema class initialization."""
    assert csv_infer_schema.name == "CSV Schema Inference"
    assert csv_infer_schema.description == "Infers schema from CSV file and creates a table in the database."
    assert csv_infer_schema.config is not None
    assert csv_infer_schema.requires_db is True
    assert csv_infer_schema.enable_llm is True


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock)
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.CSVInferSchema._infer_schema")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.CSVInferSchema._create_table")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.CSVInferSchema._insert_data")
def test_run_success(
    mock_insert_data: MagicMock,
    mock_create_table: MagicMock,
    mock_infer_schema: MagicMock,
    mock_open: MagicMock,
    csv_infer_schema: CSVInferSchema,
    csv_data: str,
) -> None:
    """Test the run method with successful execution."""
    mock_open.return_value.__enter__.return_value.read.return_value = csv_data
    mock_infer_schema.return_value = {"header1": "str", "header2": "str"}

    csv_infer_schema.run()

    mock_open.assert_called_once_with("test.csv", "r", encoding="utf-8")
    mock_infer_schema.assert_called_once_with(csv_data)
    mock_create_table.assert_called_once_with("test_table", {"header1": "str", "header2": "str"})
    mock_insert_data.assert_called_once_with("test.csv", "test_table", {"header1": "str", "header2": "str"})
    csv_infer_schema.logger.info.assert_called_with("Successfully created table test_table from test.csv")


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.CSVInferSchema._infer_schema")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.CSVInferSchema._create_table")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.CSVInferSchema._insert_data")
def test_run_value_error(
    mock_insert_data: MagicMock,
    mock_create_table: MagicMock,
    mock_infer_schema: MagicMock,
    csv_infer_schema: CSVInferSchema,
) -> None:
    """Test the run method with missing configuration values."""
    csv_infer_schema.config["csv_file_path"] = None

    with pytest.raises(ValueError):
        csv_infer_schema.run()

    csv_infer_schema.logger.error.assert_called_with("CSV file path or table name not provided in config.")
    mock_infer_schema.assert_not_called()
    mock_create_table.assert_not_called()
    mock_insert_data.assert_not_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", side_effect=FileNotFoundError)
def test_run_file_not_found_error(
    mock_open: MagicMock,
    csv_infer_schema: CSVInferSchema,
) -> None:
    """Test the run method when the CSV file is not found."""
    with pytest.raises(FileNotFoundError):
        csv_infer_schema.run()

    csv_infer_schema.logger.error.assert_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.generate_schema_from_data")
def test_infer_schema_success(
    mock_generate_schema: MagicMock,
    csv_infer_schema: CSVInferSchema,
    csv_data: str,
) -> None:
    """Test the _infer_schema method with successful schema inference."""
    mock_generate_schema.return_value = {"header1": "str", "header2": "str"}

    schema = csv_infer_schema._infer_schema(csv_data)

    assert schema == {"header1": "str", "header2": "str"}
    mock_generate_schema.assert_called_once_with(csv_data, llm_client=csv_infer_schema.llm_client)
    csv_infer_schema.logger.info.assert_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.generate_schema_from_data", side_effect=Exception("LLM Error"))
def test_infer_schema_failure(
    mock_generate_schema: MagicMock,
    csv_infer_schema: CSVInferSchema,
    csv_data: str,
) -> None:
    """Test the _infer_schema method with a failure during schema inference."""
    with pytest.raises(Exception, match="LLM Error"):
        csv_infer_schema._infer_schema(csv_data)

    mock_generate_schema.assert_called_once_with(csv_data, llm_client=csv_infer_schema.llm_client)
    csv_infer_schema.logger.error.assert_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.create_table")
def test_create_table_success(
    mock_create_table: MagicMock,
    csv_infer_schema: CSVInferSchema,
) -> None:
    """Test the _create_table method with successful table creation."""
    schema = {"header1": "str", "header2": "str"}

    csv_infer_schema._create_table("test_table", schema)

    mock_create_table.assert_called_once_with(csv_infer_schema.db_conn, "test_table", schema)
    csv_infer_schema.logger.info.assert_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.create_table", side_effect=Exception("DB Error"))
def test_create_table_failure(
    mock_create_table: MagicMock,
    csv_infer_schema: CSVInferSchema,
) -> None:
    """Test the _create_table method with a failure during table creation."""
    schema = {"header1": "str", "header2": "str"}

    with pytest.raises(Exception, match="DB Error"):
        csv_infer_schema._create_table("test_table", schema)

    mock_create_table.assert_called_once_with(csv_infer_schema.db_conn, "test_table", schema)
    csv_infer_schema.logger.error.assert_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.insert_data")
def test_insert_data_success(
    mock_insert_data: MagicMock,
    csv_infer_schema: CSVInferSchema,
) -> None:
    """Test the _insert_data method with successful data insertion."""
    schema = {"header1": "str", "header2": "str"}

    csv_infer_schema._insert_data("test.csv", "test_table", schema)

    mock_insert_data.assert_called_once_with(csv_infer_schema.db_conn, "test.csv", "test_table", schema)
    csv_infer_schema.logger.info.assert_called()


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.insert_data", side_effect=Exception("DB Error"))
def test_insert_data_failure(
    mock_insert_data: MagicMock,
    csv_infer_schema: CSVInferSchema,
) -> None:
    """Test the _insert_data method with a failure during data insertion."""
    schema = {"header1": "str", "header2": "str"}

    with pytest.raises(Exception, match="DB Error"):
        csv_infer_schema._insert_data("test.csv", "test_table", schema)

    mock_insert_data.assert_called_once_with(csv_infer_schema.db_conn, "test.csv", "test_table", schema)
    csv_infer_schema.logger.error.assert_called()


def test_get_config_value(csv_infer_schema: CSVInferSchema) -> None:
    """Test the get_config_value method."""
    csv_infer_schema.config = {"level1": {"level2": "value"}}
    assert csv_infer_schema.get_config_value("level1.level2") == "value"
    assert csv_infer_schema.get_config_value("level1.level3", "default") == "default"
    assert csv_infer_schema.get_config_value("level3", "default") == "default"
    assert csv_infer_schema.get_config_value("level3") is None


def test_get_path(csv_infer_schema: CSVInferSchema) -> None:
    """Test the get_path method."""
    project_root = csv_infer_schema.PROJECT_ROOT
    assert csv_infer_schema.get_path("test.txt") == project_root / "test.txt"
    assert csv_infer_schema.get_path("/absolute/path/test.txt") == Path("/absolute/path/test.txt")


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.load_dotenv")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.logging.basicConfig")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.logging.getLogger")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.yaml.safe_load")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.get_connection")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.get_llm_client")
def test_base_script_initialization_with_mocks(
    mock_get_llm_client: MagicMock, mock_get_connection: MagicMock, mock_safe_load: MagicMock, mock_get_logger: MagicMock, mock_basic_config: MagicMock, mock_load_dotenv: MagicMock, ) -> None:
    """Test BaseScript initialization with mocks to isolate dependencies."""
    # Mock configuration data
    mock_safe_load.return_value=None, "llm": {}}

    # Mock database connection and LLM client
    mock_get_connection.return_value=None, caplog: pytest.LogCaptureFixture) -> None:
    """Test _setup_logging with default configuration when config loading fails."""
    # Patch CONFIG_PATH to simulate config file not found
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.CONFIG_PATH", new=MagicMock()):
        if ) -> None:
    """Test BaseScript initialization with mocks to isolate dependencies."""
    # Mock configuration data
    mock_safe_load.return_value is None:
            ) -> None:
    """Test BaseScript initialization with mocks to isolate dependencies."""
    # Mock configuration data
    mock_safe_load.return_value = {"core": {"logging": {}}
        if "llm": {}}

    # Mock database connection and LLM client
    mock_get_connection.return_value is None:
            "llm": {}}

    # Mock database connection and LLM client
    mock_get_connection.return_value = MagicMock(spec=DatabaseConnection)
    mock_get_llm_client.return_value = MagicMock()

    # Create an instance of CSVInferSchema (which inherits from BaseScript)
    script = CSVInferSchema(config_section="test_section")

    # Assertions to verify correct initialization
    assert script.name == "CSV Schema Inference"
    assert script.config_section == "test_section"
    assert script.requires_db is True
    assert script.enable_llm is True
    assert script.logger is not None
    assert script.db_conn is not None
    assert script.llm_client is not None

    # Verify that mocks were called
    mock_load_dotenv.assert_called_once()
    mock_basic_config.assert_called()
    mock_get_logger.assert_called_with("CSV Schema Inference")
    mock_safe_load.assert_called()
    mock_get_connection.assert_called()
    mock_get_llm_client.assert_called()


def test_setup_logging_default_config(csv_infer_schema: CSVInferSchema
        csv_infer_schema._setup_logging()

    # Log a message to ensure logging is configured
    csv_infer_schema.logger.info("Test log message")

    # Assert that the log message was captured with the correct format and level
    assert "INFO - CSV Schema Inference - Test log message" in caplog.text


def test_setup_logging_custom_config(csv_infer_schema: CSVInferSchema, caplog: pytest.LogCaptureFixture) -> None:
    """Test _setup_logging with custom configuration from dewey.yaml."""
    # Define a custom logging configuration
    custom_log_config = {
        "core": {
            "logging": {
                "level": "DEBUG",
                "format": "%(levelname)s: %(message)s",
                "date_format": "%Y-%m-%d",
            }
        }
    }

    # Patch yaml.safe_load to return the custom configuration
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value = io.StringIO(yaml.dump(custom_log_config))
        csv_infer_schema._setup_logging()

    # Log a message to ensure logging is configured
    csv_infer_schema.logger.debug("Test log message with custom config")

    # Assert that the log message was captured with the correct format and level
    assert "DEBUG: Test log message with custom config" in caplog.text


def test_load_config_success(csv_infer_schema: CSVInferSchema) -> None:
    """Test _load_config method with successful loading."""
    # Define a sample configuration
    sample_config = {"key1": "value1", "key2": {"nested_key": "nested_value"}}

    # Patch yaml.safe_load to return the sample configuration
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value = io.StringIO(yaml.dump(sample_config))
        config = csv_infer_schema._load_config()

    # Assert that the loaded configuration matches the sample configuration
    assert config == sample_config


def test_load_config_file_not_found(csv_infer_schema: CSVInferSchema) -> None:
    """Test _load_config method when the configuration file is not found."""
    # Patch CONFIG_PATH to simulate config file not found
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.CONFIG_PATH", new=MagicMock()):
        with pytest.raises(FileNotFoundError):
            csv_infer_schema._load_config()


def test_load_config_yaml_error(csv_infer_schema: CSVInferSchema) -> None:
    """Test _load_config method when there is a YAML error in the configuration file."""
    # Patch yaml.safe_load to raise a yaml.YAMLError
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value = io.StringIO("invalid yaml")
        with pytest.raises(yaml.YAMLError):
            csv_infer_schema._load_config()


def test_load_config_with_config_section(csv_infer_schema: CSVInferSchema) -> None:
    """Test _load_config method with a specific config section."""
    # Define a sample configuration with multiple sections
    sample_config = {
        "section1": {"key1": "value1"},
        "section2": {"key2": "value2"},
    }

    # Patch yaml.safe_load to return the sample configuration
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value = io.StringIO(yaml.dump(sample_config))
        csv_infer_schema.config_section = "section2"
        config = csv_infer_schema._load_config()

    # Assert that the loaded configuration matches the specified section
    assert config == {"key2": "value2"}


def test_load_config_with_missing_config_section(csv_infer_schema: CSVInferSchema) -> None:
    """Test _load_config method with a missing config section."""
    # Define a sample configuration
    sample_config = {"section1": {"key1": "value1"}}

    # Patch yaml.safe_load to return the sample configuration
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value = io.StringIO(yaml.dump(sample_config))
        csv_infer_schema.config_section = "section2"  # Missing section
        config = csv_infer_schema._load_config()

    # Assert that the loaded configuration is the full config
    assert config == sample_config


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.argparse.ArgumentParser.parse_args")
def test_parse_args_log_level(mock_parse_args: MagicMock, csv_infer_schema: CSVInferSchema, caplog: pytest.LogCaptureFixture) -> None:
    """Test parse_args method with log level argument."""
    # Mock the command-line arguments
    mock_parse_args.return_value = MagicMock(log_level="DEBUG", config=None)

    # Call the parse_args method
    csv_infer_schema.parse_args()

    # Assert that the log level is set correctly
    assert csv_infer_schema.logger.level == logging.DEBUG
    assert "Log level set to DEBUG" in caplog.text


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.argparse.ArgumentParser.parse_args")
def test_parse_args_config_file(mock_parse_args: MagicMock, csv_infer_schema: CSVInferSchema) -> None:
    """Test parse_args method with config file argument."""
    # Mock the command-line arguments
    mock_parse_args.return_value = MagicMock(log_level=None, config="test_config.yaml")

    # Mock the configuration file content
    mock_config_content = {"key": "value"}
    with patch("dewey.core.crm.data_ingestion.csv_schema_infer.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value = io.StringIO(yaml.dump(mock_config_content))

        # Call the parse_args method
        csv_infer_schema.parse_args()

    # Assert that the configuration is loaded correctly
    assert csv_infer_schema.config == mock_config_content


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.argparse.ArgumentParser.parse_args")
def test_parse_args_config_file_not_found(mock_parse_args: MagicMock, csv_infer_schema: CSVInferSchema) -> None:
    """Test parse_args method when the config file is not found."""
    # Mock the command-line arguments
    mock_parse_args.return_value = MagicMock(log_level=None, config="nonexistent_config.yaml")

    # Call the parse_args method and assert that it exits
    with pytest.raises(SystemExit) as exc_info:
        csv_infer_schema.parse_args()

    # Assert that the exit code is 1
    assert exc_info.value.code == 1


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.argparse.ArgumentParser.parse_args")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.get_connection")
def test_parse_args_db_connection_string(mock_get_connection: MagicMock, mock_parse_args: MagicMock, csv_infer_schema: CSVInferSchema) -> None:
    """Test parse_args method with database connection string argument."""
    # Mock the command-line arguments
    mock_parse_args.return_value = MagicMock(log_level=None, config=None, db_connection_string="test_db_string")

    # Call the parse_args method
    csv_infer_schema.parse_args()

    # Assert that get_connection is called with the correct connection string
    mock_get_connection.assert_called_with({"connection_string": "test_db_string"})


@patch("dewey.core.crm.data_ingestion.csv_schema_infer.argparse.ArgumentParser.parse_args")
@patch("dewey.core.crm.data_ingestion.csv_schema_infer.get_llm_client")
def test_parse_args_llm_model(mock_get_llm_client: MagicMock, mock_parse_args: MagicMock, csv_infer_schema: CSVInferSchema) -> None:
    """Test parse_args method with LLM model argument."""
    # Mock the command-line arguments
    mock_parse_args.return_value = MagicMock(log_level=None, config=None, llm_model="test_llm_model")

    # Call the parse_args method
    csv_infer_schema.parse_args()

    # Assert that get_llm_client is called with the correct model
    mock_get_llm_client.assert_called_with({"model": "test_llm_model"})


def test_execute_keyboard_interrupt(csv_infer_schema: CSVInferSchema) -> None:
    """Test execute method with KeyboardInterrupt."""
    # Mock parse_args to return a MagicMock object
    csv_infer_schema.parse_args = MagicMock()

    # Mock run to raise a KeyboardInterrupt
    csv_infer_schema.run = MagicMock(side_effect=KeyboardInterrupt)

    # Call execute and assert that it exits with code 1
    with pytest.raises(SystemExit) as exc_info:
        csv_infer_schema.execute()

    # Assert that the exit code is 1
    assert exc_info.value.code == 1


def test_execute_exception(csv_infer_schema: CSVInferSchema) -> None:
    """Test execute method with a generic Exception."""
    # Mock parse_args to return a MagicMock object
    csv_infer_schema.parse_args = MagicMock()

    # Mock run to raise a generic Exception
    csv_infer_schema.run = MagicMock(side_effect=Exception("Test Exception"))

    # Call execute and assert that it exits with code 1
    with pytest.raises(SystemExit) as exc_info:
        csv_infer_schema.execute()

    # Assert that the exit code is 1
    assert exc_info.value.code == 1


def test_cleanup(csv_infer_schema: CSVInferSchema) -> None:
    """Test _cleanup method."""
    # Mock the database connection
    mock_db_conn = MagicMock()
    csv_infer_schema.db_conn = mock_db_conn

    # Call _cleanup
    csv_infer_schema._cleanup()

    # Assert that the database connection is closed
    mock_db_conn.close.assert_called_once()


def test_cleanup_no_db_conn(csv_infer_schema: CSVInferSchema) -> None:
    """Test _cleanup method when db_conn is None."""
    # Set db_conn to None
    csv_infer_schema.db_conn = None

    # Call _cleanup
    csv_infer_schema._cleanup()

    # Assert that no exception is raised


def test_cleanup_db_conn_exception(csv_infer_schema: CSVInferSchema) -> None:
    """Test _cleanup method when closing the database connection raises an exception."""
    # Mock the database connection
    mock_db_conn = MagicMock()
    mock_db_conn.close.side_effect = Exception("Test Exception")
    csv_infer_schema.db_conn = mock_db_conn

    # Call _cleanup
    csv_infer_schema._cleanup()

    # Assert that the exception is logged
    csv_infer_schema.logger.warning.assert_called()
