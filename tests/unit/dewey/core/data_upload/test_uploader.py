import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.data_upload.uploader import Uploader


class TestUploader:
    """Test suite for the Uploader class."""

    @pytest.fixture
    def uploader(self) -> Uploader:
        """Fixture to create an instance of the Uploader class."""
        return Uploader()

    def test_uploader_initialization(self, uploader: Uploader) -> None:
        """Test that the Uploader is initialized correctly."""
        assert uploader.name == "Uploader"
        assert uploader.config_section == "uploader"
        assert uploader.requires_db is False
        assert uploader.enable_llm is False
        assert uploader.logger is not None

    @patch("dewey.core.data_upload.uploader.Uploader.get_config_value")
    def test_run_method(self, mock_get_config_value: MagicMock, uploader: Uploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method of the Uploader class."""
        mock_get_config_value.return_value = "http://example.com/upload"
        with caplog.at_level(logging.INFO):
            uploader.run()
        assert "Starting data upload process." in caplog.text
        assert "Upload URL: http://example.com/upload" in caplog.text
        assert "Data upload process completed." in caplog.text
        mock_get_config_value.assert_called_once_with("upload_url")

    @patch("dewey.core.data_upload.uploader.Uploader.logger")
    def test_some_method(self, mock_logger: MagicMock, uploader: Uploader) -> None:
        """Test the some_method method of the Uploader class."""
        arg1 = "test_string"
        arg2 = 123
        expected_result = f"Processed {arg1} and {arg2}"

        result = uploader.some_method(arg1, arg2)

        mock_logger.info.assert_called_once_with(f"Executing some_method with arg1: {arg1}, arg2: {arg2}")
        mock_logger.debug.assert_called_once_with(f"some_method result: {expected_result}")
        assert result == expected_result

    def test_get_config_value_existing_key(self, uploader: Uploader) -> None:
        """Test get_config_value method with an existing key."""
        uploader.config = {"test_key": "test_value"}
        value = uploader.get_config_value("test_key")
        assert value == "test_value"

    def test_get_config_value_nested_key(self, uploader: Uploader) -> None:
        """Test get_config_value method with a nested key."""
        uploader.config = {"nested": {"test_key": "test_value"}}
        value = uploader.get_config_value("nested.test_key")
        assert value == "test_value"

    def test_get_config_value_default_value(self, uploader: Uploader) -> None:
        """Test get_config_value method with a default value."""
        value = uploader.get_config_value("non_existent_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_non_existent_key(self, uploader: Uploader) -> None:
        """Test get_config_value method with a non-existent key and no default value."""
        uploader.config = {}
        value = uploader.get_config_value("non_existent_key")
        assert value is None

    def test_get_config_value_intermediate_key_missing(self, uploader: Uploader) -> None:
        """Test get_config_value when an intermediate key in the path is missing."""
        uploader.config = {"top_level": {}}
        value = uploader.get_config_value("top_level.missing_level.test_key", "default_value")
        assert value == "default_value"

    @patch("dewey.core.data_upload.uploader.CONFIG_PATH", "/path/that/does/not/exist/dewey.yaml")
    def test_load_config_file_not_found(self, uploader: Uploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test _load_config method when the configuration file is not found."""
        with pytest.raises(FileNotFoundError), caplog.at_level(logging.ERROR):
            uploader._load_config()
        assert "Configuration file not found: /path/that/does/not/exist/dewey.yaml" in caplog.text

    @patch("dewey.core.data_upload.uploader.yaml.safe_load", side_effect=yaml.YAMLError)
    def test_load_config_yaml_error(self, mock_safe_load: MagicMock, uploader: Uploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test _load_config method when there is a YAML parsing error."""
        with pytest.raises(yaml.YAMLError), caplog.at_level(logging.ERROR):
            uploader._load_config()
        assert "Error parsing YAML configuration:" in caplog.text

    @patch("dewey.core.data_upload.uploader.CONFIG_PATH", "/path/to/valid/dewey.yaml")
    @patch("dewey.core.data_upload.uploader.yaml.safe_load")
    def test_load_config_section_not_found(self, mock_safe_load: MagicMock, uploader: Uploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test _load_config method when the specified config section is not found."""
        mock_safe_load.return_value = {"some_other_section": {"key": "value"}}
        uploader.config_section = "non_existent_section"
        with caplog.at_level(logging.WARNING):
            config = uploader._load_config()
        assert "Config section 'non_existent_section' not found in dewey.yaml. Using full config." in caplog.text
        assert config == {"some_other_section": {"key": "value"}}

    @patch("dewey.core.data_upload.uploader.CONFIG_PATH", "/path/to/valid/dewey.yaml")
    @patch("dewey.core.data_upload.uploader.yaml.safe_load")
    def test_load_config_section_found(self, mock_safe_load: MagicMock, uploader: Uploader) -> None:
        """Test _load_config method when the specified config section is found."""
        mock_safe_load.return_value = {"uploader": {"key": "value"}, "some_other_section": {"key": "value"}}
        uploader.config_section = "uploader"
        config = uploader._load_config()
        assert config == {"key": "value"}

    @patch("dewey.core.data_upload.uploader.CONFIG_PATH", "/path/to/valid/dewey.yaml")
    @patch("dewey.core.data_upload.uploader.yaml.safe_load")
    def test_load_config_no_section(self, mock_safe_load: MagicMock, uploader: Uploader) -> None:
        """Test _load_config method when no config section is specified."""
        mock_safe_load.return_value = {"uploader": {"key": "value"}}
        uploader.config_section = None
        config = uploader._load_config()
        assert config == {"uploader": {"key": "value"}}

    @patch("dewey.core.data_upload.uploader.load_dotenv")
    def test_init_loads_dotenv(self, mock_load_dotenv: MagicMock) -> None:
        """Test that the __init__ method loads environment variables from .env file."""
        Uploader()
        mock_load_dotenv.assert_called_once_with(Uploader.PROJECT_ROOT / ".env")

    @patch("dewey.core.data_upload.uploader.logging.basicConfig")
    def test_setup_logging_default_config(self, mock_basicConfig: MagicMock, uploader: Uploader) -> None:
        """Test _setup_logging method with default logging configuration."""
        uploader._setup_logging()
        mock_basicConfig.assert_called_once()
        kwargs = mock_basicConfig.call_args[1]
        assert kwargs["level"] == logging.INFO
        assert kwargs["format"] == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        assert kwargs["datefmt"] == '%Y-%m-%d %H:%M:%S'

    @patch("dewey.core.data_upload.uploader.logging.basicConfig")
    @patch("dewey.core.data_upload.uploader.CONFIG_PATH", "/path/to/valid/dewey.yaml")
    @patch("dewey.core.data_upload.uploader.yaml.safe_load")
    def test_setup_logging_custom_config(self, mock_safe_load: MagicMock, mock_basicConfig: MagicMock, uploader: Uploader) -> None:
        """Test _setup_logging method with custom logging configuration from config file."""
        mock_safe_load.return_value = {
            "core": {
                "logging": {
                    "level": "DEBUG",
                    "format": "%(levelname)s - %(message)s",
                    "date_format": "%m/%d/%Y %H:%M:%S",
                }
            }
        }
        uploader._setup_logging()
        mock_basicConfig.assert_called_once()
        kwargs = mock_basicConfig.call_args[1]
        assert kwargs["level"] == logging.DEBUG
        assert kwargs["format"] == '%(levelname)s - %(message)s'
        assert kwargs["datefmt"] == '%m/%d/%Y %H:%M:%S'

    @patch("dewey.core.data_upload.uploader.logging.basicConfig")
    @patch("dewey.core.data_upload.uploader.CONFIG_PATH", "/path/to/valid/dewey.yaml")
    @patch("dewey.core.data_upload.uploader.yaml.safe_load", side_effect=FileNotFoundError)
    def test_setup_logging_config_file_not_found(self, mock_safe_load: MagicMock, mock_basicConfig: MagicMock, uploader: Uploader) -> None:
        """Test _setup_logging method when the config file is not found."""
        uploader._setup_logging()
        mock_basicConfig.assert_called_once()
        kwargs = mock_basicConfig.call_args[1]
        assert kwargs["level"] == logging.INFO
        assert kwargs["format"] == '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        assert kwargs["datefmt"] == '%Y-%m-%d %H:%M:%S'

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    def test_setup_argparse(self, mock_argparse: MagicMock, uploader: Uploader) -> None:
        """Test setup_argparse method."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_parser.add_argument.return_value = None

        parser = uploader.setup_argparse()

        assert parser == mock_parser
        assert mock_argparse.call_count == 1
        mock_parser.add_argument.assert_called()

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    def test_setup_argparse_with_db(self, mock_argparse: MagicMock) -> None:
        """Test setup_argparse method when database is required."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_parser.add_argument.return_value = None

        uploader = Uploader(requires_db=True)
        parser = uploader.setup_argparse()

        assert parser == mock_parser
        assert mock_argparse.call_count == 1
        assert mock_parser.add_argument.call_count >= 1
        mock_parser.add_argument.assert_called_with(
            "--db-connection-string",
            help="Database connection string (overrides config)"
        )

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    def test_setup_argparse_with_llm(self, mock_argparse: MagicMock) -> None:
        """Test setup_argparse method when LLM is enabled."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_parser.add_argument.return_value = None

        uploader = Uploader(enable_llm=True)
        parser = uploader.setup_argparse()

        assert parser == mock_parser
        assert mock_argparse.call_count == 1
        assert mock_parser.add_argument.call_count >= 1
        mock_parser.add_argument.assert_called_with(
            "--llm-model",
            help="LLM model to use (overrides config)"
        )

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    def test_parse_args_updates_log_level(self, mock_argparse: MagicMock, uploader: Uploader) -> None:
        """Test parse_args method updates log level."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_parser.parse_args.return_value = mock_args

        with patch.object(uploader.logger, "setLevel") as mock_set_level:
            uploader.parse_args()
            mock_set_level.assert_called_once_with(logging.DEBUG)

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    @patch("dewey.core.data_upload.uploader.Path.exists")
    @patch("dewey.core.data_upload.uploader.yaml.safe_load")
    def test_parse_args_updates_config(self, mock_safe_load: MagicMock, mock_exists: MagicMock, mock_argparse: MagicMock, uploader: Uploader) -> None:
        """Test parse_args method updates config."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.config = "/path/to/config.yaml"
        mock_args.log_level = None
        mock_parser.parse_args.return_value = mock_args
        mock_exists.return_value = True
        mock_safe_load.return_value = {"key": "value"}

        uploader.parse_args()

        assert uploader.config == {"key": "value"}

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    @patch("dewey.core.data_upload.uploader.Path.exists")
    def test_parse_args_config_file_not_found(self, mock_exists: MagicMock, mock_argparse: MagicMock, uploader: Uploader, capsys: pytest.CaptureFixture) -> None:
        """Test parse_args method when config file is not found."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.config = "/path/to/config.yaml"
        mock_args.log_level = None
        mock_parser.parse_args.return_value = mock_args
        mock_exists.return_value = False

        with pytest.raises(SystemExit) as excinfo:
            uploader.parse_args()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Configuration file not found: /path/to/config.yaml" in captured.err

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    def test_parse_args_updates_db_connection(self, mock_argparse: MagicMock) -> None:
        """Test parse_args method updates database connection."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.db_connection_string = "test_connection_string"
        mock_args.config = None
        mock_args.log_level = None
        mock_parser.parse_args.return_value = mock_args

        with patch("dewey.core.data_upload.uploader.get_connection") as mock_get_connection:
            uploader = Uploader(requires_db=True)
            uploader.parse_args()
            mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})

    @patch("dewey.core.data_upload.uploader.argparse.ArgumentParser")
    def test_parse_args_updates_llm_model(self, mock_argparse: MagicMock) -> None:
        """Test parse_args method updates LLM model."""
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.llm_model = "test_llm_model"
        mock_args.config = None
        mock_args.log_level = None
        mock_parser.parse_args.return_value = mock_args

        with patch("dewey.core.data_upload.uploader.get_llm_client") as mock_get_llm_client:
            uploader = Uploader(enable_llm=True)
            uploader.parse_args()
            mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})

    def test_get_path_absolute(self, uploader: Uploader) -> None:
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path/to/file.txt"
        result = uploader.get_path(absolute_path)
        assert result == Path(absolute_path)

    def test_get_path_relative(self, uploader: Uploader) -> None:
        """Test get_path method with a relative path."""
        relative_path = "relative/path/to/file.txt"
        expected_path = Uploader.PROJECT_ROOT / relative_path
        result = uploader.get_path(relative_path)
        assert result == expected_path

    @patch("dewey.core.data_upload.uploader.Uploader.parse_args")
    @patch("dewey.core.data_upload.uploader.Uploader.run")
    def test_execute_success(self, mock_run: MagicMock, mock_parse_args: MagicMock, uploader: Uploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test execute method with successful script execution."""
        mock_parse_args.return_value = MagicMock()
        with caplog.at_level(logging.INFO):
            uploader.execute()
        assert "Starting execution of Uploader" in caplog.text
        assert "Completed execution of Uploader" in caplog.text
        mock_run.assert_called_once()

    @patch("dewey.core.data_upload.uploader.Uploader.parse_args")
    @patch("dewey.core.data_upload.uploader.Uploader.run", side_effect=KeyboardInterrupt)
    def test_execute_keyboard_interrupt(self, mock_run: MagicMock, mock_parse_args: MagicMock, uploader: Uploader, capsys: pytest.CaptureFixture) -> None:
        """Test execute method with KeyboardInterrupt."""
        mock_parse_args.return_value = MagicMock()
        with pytest.raises(SystemExit) as excinfo:
            uploader.execute()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Script interrupted by user" in captured.err

    @patch("dewey.core.data_upload.uploader.Uploader.parse_args")
    @patch("dewey.core.data_upload.uploader.Uploader.run", side_effect=ValueError("Test Error"))
    def test_execute_exception(self, mock_run: MagicMock, mock_parse_args: MagicMock, uploader: Uploader, capsys: pytest.CaptureFixture) -> None:
        """Test execute method with an exception during script execution."""
        mock_parse_args.return_value = MagicMock()
        with pytest.raises(SystemExit) as excinfo:
            uploader.execute()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error executing script: Test Error" in captured.err

    @patch("dewey.core.data_upload.uploader.Uploader.db_conn")
    def test_cleanup_closes_db_connection(self, mock_db_conn: MagicMock, uploader: Uploader) -> None:
        """Test _cleanup method closes the database connection."""
        uploader.db_conn = mock_db_conn
        uploader._cleanup()
        mock_db_conn.close.assert_called_once()

    @patch("dewey.core.data_upload.uploader.Uploader.db_conn")
    def test_cleanup_handles_db_close_exception(self, mock_db_conn: MagicMock, uploader: Uploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test _cleanup method handles exceptions during database connection close."""
        mock_db_conn.close.side_effect = ValueError("Close Error")
        uploader.db_conn = mock_db_conn
        with caplog.at_level(logging.WARNING):
            uploader._cleanup()
        assert "Error closing database connection: Close Error" in caplog.text

    def test_cleanup_no_db_connection(self, uploader: Uploader) -> None:
        """Test _cleanup method when there is no database connection."""
        uploader.db_conn = None
        uploader._cleanup()
        # Assert that no exception is raised and no methods are called on a None object.
        assert True
