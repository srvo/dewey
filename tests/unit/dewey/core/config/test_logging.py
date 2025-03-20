import logging
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from dewey.core.config.logging import LoggingExample


class TestLoggingExample:
    """Tests for the LoggingExample class."""

    @pytest.fixture
    def logging_example(self) -> LoggingExample:
        """Fixture for creating a LoggingExample instance."""
        return LoggingExample()

    def test_init(self, logging_example: LoggingExample) -> None:
        """Tests the __init__ method."""
        assert logging_example.name == "LoggingExample"
        assert logging_example.config_section == "logging"
        assert logging_example.requires_db is False
        assert logging_example.enable_llm is False
        assert isinstance(logging_example.logger, logging.Logger)

    @patch("dewey.core.config.logging.LoggingExample.get_config_value")
    def test_run(
        self,
        mock_get_config_value: Any,
        logging_example: LoggingExample,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the run method."""
        mock_get_config_value.return_value = "test_value"
        caplog.set_level(logging.INFO)
        logging_example.run()

        assert "Starting the LoggingExample script." in caplog.text
        assert "Example config value: test_value" in caplog.text
        assert "This is a warning message." in caplog.text
        assert "This is an error message." in caplog.text
        assert "Finished the LoggingExample script." in caplog.text

        assert "WARNING" in caplog.text
        assert "ERROR" in caplog.text

        assert mock_get_config_value.call_count == 1
        mock_get_config_value.assert_called_with("example_config", "default_value")

    @patch("dewey.core.config.logging.LoggingExample.parse_args")
    @patch("dewey.core.config.logging.LoggingExample.run")
    def test_execute(
        self,
        mock_run: Any,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the execute method."""
        mock_parse_args.return_value = None
        caplog.set_level(logging.INFO)
        logging_example.execute()

        assert "Starting execution of LoggingExample" in caplog.text
        assert "Completed execution of LoggingExample" in caplog.text
        assert mock_run.call_count == 1

    @patch("dewey.core.config.logging.LoggingExample.parse_args")
    def test_execute_keyboard_interrupt(
        self,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the execute method with KeyboardInterrupt."""
        mock_parse_args.return_value = None
        logging_example.run = lambda: (_ for _ in ()).throw(KeyboardInterrupt)  # type: ignore
        caplog.set_level(logging.WARNING)
        logging_example.execute()

        assert "Script interrupted by user" in caplog.text

    @patch("dewey.core.config.logging.LoggingExample.parse_args")
    def test_execute_exception(
        self,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the execute method with a generic Exception."""
        mock_parse_args.return_value = None
        logging_example.run = lambda: (_ for _ in ()).throw(Exception("Test Exception"))  # type: ignore
        caplog.set_level(logging.ERROR)
        logging_example.execute()

        assert "Error executing script: Test Exception" in caplog.text

    def test_get_path(self, logging_example: LoggingExample) -> None:
        """Tests the get_path method."""
        # Test with relative path
        relative_path = "config/dewey.yaml"
        expected_path = logging_example.PROJECT_ROOT / relative_path
        assert logging_example.get_path(relative_path) == expected_path

        # Test with absolute path
        absolute_path = "/tmp/test.txt"
        assert logging_example.get_path(absolute_path) == Path(absolute_path)

    def test_get_config_value(self, logging_example: LoggingExample) -> None:
        """Tests the get_config_value method."""
        # Mock the config attribute
        logging_example.config = {"level1": {"level2": "value"}}

        # Test with valid key
        assert logging_example.get_config_value("level1.level2") == "value"

        # Test with invalid key and default value
        assert logging_example.get_config_value("level1.level3", "default") == "default"

        # Test with invalid key and no default value
        assert logging_example.get_config_value("level2", None) is None

    @patch("logging.basicConfig")
    def test_setup_logging_from_config(
        self, mock_basicConfig: Any, logging_example: LoggingExample, tmp_path: Path
    ) -> None:
        """Tests the _setup_logging method when config is available."""
        # Create a temporary config file
        config_data = {
            "core": {
                "logging": {
                    "level": "DEBUG",
                    "format": "%(levelname)s - %(message)s",
                    "date_format": "%Y-%m-%d",
                }
            }
        }
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_file):
            logging_example._setup_logging()

        # Assert that basicConfig was called with the correct arguments
        mock_basicConfig.assert_called_once_with(
            level=logging.DEBUG,
            format="%(levelname)s - %(message)s",
            datefmt="%Y-%m-%d",
        )
        assert isinstance(logging_example.logger, logging.Logger)

    @patch("logging.basicConfig")
    def test_setup_logging_default_config(
        self, mock_basicConfig: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _setup_logging method when config is not available."""
        # Patch the CONFIG_PATH to a non-existent file
        with patch("dewey.core.base_script.CONFIG_PATH", "non_existent_file.yaml"):
            logging_example._setup_logging()

        # Assert that basicConfig was called with the default arguments
        mock_basicConfig.assert_called_once_with(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        assert isinstance(logging_example.logger, logging.Logger)

    def test_load_config_success(
        self, logging_example: LoggingExample, tmp_path: Path
    ) -> None:
        """Tests the _load_config method when the config file is loaded successfully."""
        # Create a temporary config file
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_file):
            config = logging_example._load_config()

        # Assert that the config is loaded correctly
        assert config == config_data

    def test_load_config_section_success(
        self, logging_example: LoggingExample, tmp_path: Path
    ) -> None:
        """Tests the _load_config method when a specific config section is loaded successfully."""
        # Create a temporary config file
        config_data = {
            "section1": {"test_key": "test_value"},
            "section2": {"other_key": "other_value"},
        }
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_file):
            logging_example.config_section = "section1"
            config = logging_example._load_config()

        # Assert that the config is loaded correctly
        assert config == config_data["section1"]

    def test_load_config_section_not_found(
        self,
        logging_example: LoggingExample,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the _load_config method when the specified config section is not found."""
        # Create a temporary config file
        config_data = {"section1": {"test_key": "test_value"}}
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.base_script.CONFIG_PATH", config_file):
            logging_example.config_section = "section2"
            caplog.set_level(logging.WARNING)
            config = logging_example._load_config()

        # Assert that a warning is logged and the full config is returned
        assert (
            "Config section 'section2' not found in dewey.yaml. Using full config."
            in caplog.text
        )
        assert config == config_data

    def test_load_config_file_not_found(self, logging_example: LoggingExample) -> None:
        """Tests the _load_config method when the config file is not found."""
        # Patch the CONFIG_PATH to a non-existent file
        with (
            patch("dewey.core.base_script.CONFIG_PATH", "non_existent_file.yaml"),
            pytest.raises(FileNotFoundError),
        ):
            logging_example._load_config()

    def test_load_config_invalid_yaml(
        self, logging_example: LoggingExample, tmp_path: Path
    ) -> None:
        """Tests the _load_config method when the config file contains invalid YAML."""
        # Create a temporary config file with invalid YAML
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content")

        # Patch the CONFIG_PATH to point to the temporary config file
        with (
            patch("dewey.core.base_script.CONFIG_PATH", config_file),
            pytest.raises(yaml.YAMLError),
        ):
            logging_example._load_config()

    @patch("dewey.core.config.logging.get_connection")
    def test_initialize_db_connection_success(
        self, mock_get_connection: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _initialize_db_connection method when the database connection is initialized successfully."""
        # Mock the config attribute
        logging_example.config = {
            "core": {"database": {"connection_string": "test_connection_string"}}
        }
        logging_example.requires_db = True

        # Call the method
        logging_example._initialize_db_connection()

        # Assert that get_connection was called with the correct arguments
        mock_get_connection.assert_called_once_with(
            {"connection_string": "test_connection_string"}
        )
        assert logging_example.db_conn == mock_get_connection.return_value

    @patch("dewey.core.config.logging.get_connection")
    def test_initialize_db_connection_import_error(
        self, mock_get_connection: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _initialize_db_connection method when the database module cannot be imported."""
        # Mock the import of the database module to raise an ImportError
        with (
            patch.dict("sys.modules", {"dewey.core.db.connection": None}),
            pytest.raises(ImportError),
        ):
            logging_example.requires_db = True
            logging_example._initialize_db_connection()

    @patch("dewey.core.config.logging.get_connection")
    def test_initialize_db_connection_exception(
        self, mock_get_connection: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _initialize_db_connection method when an exception occurs during database connection initialization."""
        # Mock the get_connection function to raise an exception
        mock_get_connection.side_effect = Exception("Test Exception")
        logging_example.config = {
            "core": {"database": {"connection_string": "test_connection_string"}}
        }
        logging_example.requires_db = True

        # Call the method and assert that an exception is raised
        with pytest.raises(Exception, match="Test Exception"):
            logging_example._initialize_db_connection()

        assert logging_example.db_conn is None

    @patch("dewey.core.config.logging.get_llm_client")
    def test_initialize_llm_client_success(
        self, mock_get_llm_client: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _initialize_llm_client method when the LLM client is initialized successfully."""
        # Mock the config attribute
        logging_example.config = {"llm": {"model": "test_model"}}
        logging_example.enable_llm = True

        # Call the method
        logging_example._initialize_llm_client()

        # Assert that get_llm_client was called with the correct arguments
        mock_get_llm_client.assert_called_once_with({"model": "test_model"})
        assert logging_example.llm_client == mock_get_llm_client.return_value

    @patch("dewey.core.config.logging.get_llm_client")
    def test_initialize_llm_client_import_error(
        self, mock_get_llm_client: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _initialize_llm_client method when the LLM module cannot be imported."""
        # Mock the import of the LLM module to raise an ImportError
        with (
            patch.dict("sys.modules", {"dewey.llm.llm_utils": None}),
            pytest.raises(ImportError),
        ):
            logging_example.enable_llm = True
            logging_example._initialize_llm_client()

    @patch("dewey.core.config.logging.get_llm_client")
    def test_initialize_llm_client_exception(
        self, mock_get_llm_client: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _initialize_llm_client method when an exception occurs during LLM client initialization."""
        # Mock the get_llm_client function to raise an exception
        mock_get_llm_client.side_effect = Exception("Test Exception")
        logging_example.config = {"llm": {"model": "test_model"}}
        logging_example.enable_llm = True

        # Call the method and assert that an exception is raised
        with pytest.raises(Exception, match="Test Exception"):
            logging_example._initialize_llm_client()

        assert logging_example.llm_client is None

    def test_setup_argparse(self, logging_example: LoggingExample) -> None:
        """Tests the setup_argparse method."""
        parser = logging_example.setup_argparse()
        assert parser.description == logging_example.description
        assert parser._actions[1].dest == "config"
        assert parser._actions[2].dest == "log_level"

    def test_setup_argparse_with_db(self, logging_example: LoggingExample) -> None:
        """Tests the setup_argparse method when database is required."""
        logging_example.requires_db = True
        parser = logging_example.setup_argparse()
        assert parser._actions[3].dest == "db_connection_string"

    def test_setup_argparse_with_llm(self, logging_example: LoggingExample) -> None:
        """Tests the setup_argparse method when LLM is enabled."""
        logging_example.enable_llm = True
        parser = logging_example.setup_argparse()
        assert parser._actions[3].dest == "llm_model"

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args(
        self,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the parse_args method."""
        # Mock the parse_args method to return a Namespace object
        mock_args = mock_parse_args.return_value
        mock_args.log_level = "DEBUG"
        mock_args.config = str(tmp_path / "test_config.yaml")

        # Create a temporary config file
        config_data = {"test_key": "test_value"}
        with open(mock_args.config, "w") as f:
            yaml.dump(config_data, f)

        # Call the method
        caplog.set_level(logging.DEBUG)
        args = logging_example.parse_args()

        # Assert that the log level and config are updated correctly
        assert logging_example.logger.level == logging.DEBUG
        assert logging_example.config == config_data
        assert args == mock_args
        assert "Log level set to DEBUG" in caplog.text
        assert f"Loaded configuration from {mock_args.config}" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(
        self,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the parse_args method when the config file is not found."""
        # Mock the parse_args method to return a Namespace object
        mock_args = mock_parse_args.return_value
        mock_args.log_level = "DEBUG"
        mock_args.config = str(tmp_path / "non_existent_config.yaml")

        # Call the method and assert that the program exits
        with pytest.raises(SystemExit) as exc_info:
            logging_example.parse_args()

        # Assert that the error message is logged and the exit code is 1
        assert "Configuration file not found" in caplog.text
        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.config.logging.get_connection")
    def test_parse_args_db_connection_string(
        self,
        mock_get_connection: Any,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the parse_args method when a database connection string is provided."""
        # Mock the parse_args method to return a Namespace object
        mock_args = mock_parse_args.return_value
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_args.db_connection_string = "custom_connection_string"

        # Set the requires_db attribute to True
        logging_example.requires_db = True

        # Call the method
        caplog.set_level(logging.INFO)
        logging_example.parse_args()

        # Assert that the database connection is updated correctly
        mock_get_connection.assert_called_once_with(
            {"connection_string": "custom_connection_string"}
        )
        assert logging_example.db_conn == mock_get_connection.return_value
        assert "Using custom database connection" in caplog.text

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.config.logging.get_llm_client")
    def test_parse_args_llm_model(
        self,
        mock_get_llm_client: Any,
        mock_parse_args: Any,
        logging_example: LoggingExample,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the parse_args method when an LLM model is provided."""
        # Mock the parse_args method to return a Namespace object
        mock_args = mock_parse_args.return_value
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_args.llm_model = "custom_llm_model"

        # Set the enable_llm attribute to True
        logging_example.enable_llm = True

        # Call the method
        caplog.set_level(logging.INFO)
        logging_example.parse_args()

        # Assert that the LLM client is updated correctly
        mock_get_llm_client.assert_called_once_with({"model": "custom_llm_model"})
        assert logging_example.llm_client == mock_get_llm_client.return_value
        assert f"Using custom LLM model: {mock_args.llm_model}" in caplog.text

    @patch("dewey.core.config.logging.LoggingExample._cleanup")
    def test_cleanup_db_connection(
        self, mock_cleanup: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _cleanup method when a database connection exists."""
        # Mock the database connection and its close method
        mock_db_conn = pytest.MagicMock()
        logging_example.db_conn = mock_db_conn

        # Call the method
        logging_example._cleanup()

        # Assert that the close method was called
        mock_db_conn.close.assert_called_once()

    @patch("dewey.core.config.logging.LoggingExample._cleanup")
    def test_cleanup_no_db_connection(
        self, mock_cleanup: Any, logging_example: LoggingExample
    ) -> None:
        """Tests the _cleanup method when no database connection exists."""
        # Set the db_conn attribute to None
        logging_example.db_conn = None

        # Call the method
        logging_example._cleanup()

        # Assert that the close method was not called
        mock_cleanup.assert_not_called()
