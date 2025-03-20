import logging
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.data_upload import DataUploader


class TestDataUploader:
    """Unit tests for the DataUploader class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        with patch("dewey.core.data_upload.BaseScript", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def data_uploader(self) -> DataUploader:
        """Fixture to create a DataUploader instance."""
        return DataUploader()

    def test_data_uploader_initialization(self, mock_base_script: MagicMock) -> None:
        """Test DataUploader initialization."""
        uploader = DataUploader(config_section="test_section")
        mock_base_script.assert_called_once_with(
            config_section="test_section", requires_db=True, enable_llm=True
        )
        assert uploader.config_section == "test_section"

    def test_run_method_no_api_key(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test run method when API key is not found in configuration."""
        data_uploader.get_config_value = MagicMock(return_value=None)
        data_uploader.db_conn = None
        data_uploader.llm_client = None
        with caplog.records_property() as records:
            data_uploader.run()
            assert "API Key not found in configuration." in records[0].message
            assert "Database connection is not available." in records[1].message
            assert "LLM client is not available." in records[2].message
            assert "Data upload process completed successfully." in records[3].message
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[1].levelname == "ERROR"
        assert caplog.records[2].levelname == "ERROR"
        assert caplog.records[3].levelname == "INFO"

    def test_run_method_with_api_key_db_and_llm(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test run method when API key is found and DB/LLM are available."""
        data_uploader.get_config_value = MagicMock(return_value="test_api_key")
        data_uploader.db_conn = MagicMock()
        data_uploader.llm_client = MagicMock()
        data_uploader.llm_client.generate_text = MagicMock(return_value="Test LLM Response")

        with caplog.records_property() as records:
            data_uploader.run()
            assert "API Key: test_api_key" in records[0].message
            assert "Database connection is available." in records[1].message
            assert "LLM client is available." in records[2].message
            assert "Data upload process completed successfully." in records[3].message

        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.records[1].levelname == "DEBUG"
        assert caplog.records[2].levelname == "DEBUG"
        assert caplog.records[3].levelname == "INFO"
        data_uploader.db_conn.cursor.assert_not_called()
        data_uploader.llm_client.generate_text.assert_not_called()

    def test_run_method_exception(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test run method when an exception occurs."""
        data_uploader.get_config_value = MagicMock(side_effect=Exception("Test Exception"))
        with caplog.records_property() as records:
            data_uploader.run()
            assert "An error occurred during data upload: Test Exception" in records[0].message
        assert caplog.records[0].levelname == "ERROR"

    def test_execute_method(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test execute method."""
        data_uploader.parse_args = MagicMock()
        data_uploader.run = MagicMock()
        data_uploader._cleanup = MagicMock()

        data_uploader.execute()

        data_uploader.parse_args.assert_called_once()
        data_uploader.run.assert_called_once()
        data_uploader._cleanup.assert_called_once()
        assert "Starting execution of DataUploader" in caplog.text
        assert "Completed execution of DataUploader" in caplog.text

    def test_execute_method_keyboard_interrupt(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test execute method when KeyboardInterrupt is raised."""
        data_uploader.parse_args = MagicMock()
        data_uploader.run = MagicMock(side_effect=KeyboardInterrupt)
        data_uploader._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            data_uploader.execute()

        assert exc_info.value.code == 1
        data_uploader.parse_args.assert_called_once()
        data_uploader.run.assert_called_once()
        data_uploader._cleanup.assert_called_once()
        assert "Script interrupted by user" in caplog.text

    def test_execute_method_exception(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test execute method when an exception is raised."""
        data_uploader.parse_args = MagicMock()
        data_uploader.run = MagicMock(side_effect=Exception("Test Exception"))
        data_uploader._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            data_uploader.execute()

        assert exc_info.value.code == 1
        data_uploader.parse_args.assert_called_once()
        data_uploader.run.assert_called_once()
        data_uploader._cleanup.assert_called_once()
        assert "Error executing script: Test Exception" in caplog.text

    def test_cleanup_method(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test cleanup method."""
        data_uploader.db_conn = MagicMock()
        data_uploader._cleanup()
        data_uploader.db_conn.close.assert_called_once()
        assert "Closing database connection" in caplog.text

    def test_cleanup_method_no_db_conn(self, data_uploader: DataUploader) -> None:
        """Test cleanup method when db_conn is None."""
        data_uploader.db_conn = None
        data_uploader._cleanup()

    def test_cleanup_method_exception(self, data_uploader: DataUploader, caplog: pytest.LogCaptureFixture) -> None:
        """Test cleanup method when an exception occurs during db_conn.close()."""
        data_uploader.db_conn = MagicMock()
        data_uploader.db_conn.close.side_effect = Exception("Test Exception")
        data_uploader._cleanup()
        assert "Error closing database connection: Test Exception" in caplog.text

    def test_get_path_absolute(self, data_uploader: DataUploader) -> None:
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path"
        result = data_uploader.get_path(absolute_path)
        assert result == Path(absolute_path)

    def test_get_path_relative(self, data_uploader: DataUploader) -> None:
        """Test get_path method with a relative path."""
        relative_path = "relative/path"
        expected_path = Path(data_uploader.PROJECT_ROOT) / relative_path
        result = data_uploader.get_path(relative_path)
        assert result == expected_path

    def test_get_config_value_existing_key(self, data_uploader: DataUploader) -> None:
        """Test get_config_value method with an existing key."""
        data_uploader.config = {"section": {"key": "value"}}
        result = data_uploader.get_config_value("section.key")
        assert result == "value"

    def test_get_config_value_missing_key(self, data_uploader: DataUploader) -> None:
        """Test get_config_value method with a missing key."""
        data_uploader.config = {"section": {"key": "value"}}
        result = data_uploader.get_config_value("section.missing_key", "default_value")
        assert result == "default_value"

    def test_get_config_value_nested_missing_key(self, data_uploader: DataUploader) -> None:
        """Test get_config_value method with a nested missing key."""
        data_uploader.config = {"section": {"key": "value"}}
        result = data_uploader.get_config_value("missing_section.key", "default_value")
        assert result == "default_value"

    def test_get_config_value_default_none(self, data_uploader: DataUploader) -> None:
        """Test get_config_value method with a missing key and default=None."""
        data_uploader.config = {"section": {"key": "value"}}
        result = data_uploader.get_config_value("section.missing_key")
        assert result is None

    def test_setup_logging_from_config(self, data_uploader: DataUploader, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test setup_logging method with configuration from file."""
        config_data = {
            'core': {
                'logging': {
                    'level': 'DEBUG',
                    'format': '%(levelname)s - %(message)s',
                    'date_format': '%Y-%m-%d',
                }
            }
        }
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        data_uploader.CONFIG_PATH = config_file
        data_uploader._setup_logging()
        data_uploader.logger.debug("Test message")
        assert "DEBUG - Test message" in caplog.text

    def test_setup_logging_default_config(self, data_uploader: DataUploader, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test setup_logging method with default configuration."""
        config_file = tmp_path / "dewey.yaml"
        data_uploader.CONFIG_PATH = config_file
        data_uploader._setup_logging()
        data_uploader.logger.info("Test message")
        assert "INFO - dewey.core.data_upload - Test message" in caplog.text

    def test_load_config_specific_section(self, data_uploader: DataUploader, tmp_path: Path) -> None:
        """Test loading a specific config section."""
        config_data = {
            'section1': {'key1': 'value1'},
            'section2': {'key2': 'value2'}
        }
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        data_uploader.CONFIG_PATH = config_file
        data_uploader.config_section = 'section2'
        config = data_uploader._load_config()
        assert config == {'key2': 'value2'}

    def test_load_config_missing_section(self, data_uploader: DataUploader, tmp_path: Path) -> None:
        """Test loading a missing config section."""
        config_data = {
            'section1': {'key1': 'value1'},
        }
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        data_uploader.CONFIG_PATH = config_file
        data_uploader.config_section = 'section2'
        config = data_uploader._load_config()
        assert config == config_data

    def test_load_config_file_not_found(self, data_uploader: DataUploader, tmp_path: Path) -> None:
        """Test loading config when the file is not found."""
        data_uploader.CONFIG_PATH = tmp_path / "missing.yaml"
        with pytest.raises(FileNotFoundError):
            data_uploader._load_config()

    def test_load_config_invalid_yaml(self, data_uploader: DataUploader, tmp_path: Path) -> None:
        """Test loading config with invalid YAML."""
        config_file = tmp_path / "dewey.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid yaml")
        data_uploader.CONFIG_PATH = config_file
        with pytest.raises(yaml.YAMLError):
            data_uploader._load_config()

    @patch("dewey.core.data_upload.get_connection")
    def test_initialize_db_connection_success(self, mock_get_connection: MagicMock, data_uploader: DataUploader) -> None:
        """Test successful database connection initialization."""
        data_uploader.config = {'core': {'database': {'test': 'config'}}}
        data_uploader._initialize_db_connection()
        mock_get_connection.assert_called_once_with({'test': 'config'})
        assert data_uploader.db_conn == mock_get_connection.return_value

    @patch("dewey.core.data_upload.get_connection", side_effect=ImportError)
    def test_initialize_db_connection_import_error(self, mock_get_connection: MagicMock, data_uploader: DataUploader) -> None:
        """Test database connection initialization import error."""
        with pytest.raises(ImportError):
            data_uploader._initialize_db_connection()
        assert data_uploader.db_conn is None

    @patch("dewey.core.data_upload.get_connection", side_effect=Exception("Test Exception"))
    def test_initialize_db_connection_exception(self, mock_get_connection: MagicMock, data_uploader: DataUploader) -> None:
        """Test database connection initialization exception."""
        data_uploader.config = {'core': {'database': {'test': 'config'}}}
        with pytest.raises(Exception, match="Failed to initialize database connection: Test Exception"):
            data_uploader._initialize_db_connection()
        assert data_uploader.db_conn is None

    @patch("dewey.core.data_upload.get_llm_client")
    def test_initialize_llm_client_success(self, mock_get_llm_client: MagicMock, data_uploader: DataUploader) -> None:
        """Test successful LLM client initialization."""
        data_uploader.config = {'llm': {'test': 'config'}}
        data_uploader._initialize_llm_client()
        mock_get_llm_client.assert_called_once_with({'test': 'config'})
        assert data_uploader.llm_client == mock_get_llm_client.return_value

    @patch("dewey.core.data_upload.get_llm_client", side_effect=ImportError)
    def test_initialize_llm_client_import_error(self, mock_get_llm_client: MagicMock, data_uploader: DataUploader) -> None:
        """Test LLM client initialization import error."""
        with pytest.raises(ImportError):
            data_uploader._initialize_llm_client()
        assert data_uploader.llm_client is None

    @patch("dewey.core.data_upload.get_llm_client", side_effect=Exception("Test Exception"))
    def test_initialize_llm_client_exception(self, mock_get_llm_client: MagicMock, data_uploader: DataUploader) -> None:
        """Test LLM client initialization exception."""
        data_uploader.config = {'llm': {'test': 'config'}}
        with pytest.raises(Exception, match="Failed to initialize LLM client: Test Exception"):
            data_uploader._initialize_llm_client()
        assert data_uploader.llm_client is None

    def test_setup_argparse(self, data_uploader: DataUploader) -> None:
        """Test setup_argparse method."""
        parser = data_uploader.setup_argparse()
        assert parser.description == data_uploader.description
        assert parser.format_help()

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args: MagicMock, data_uploader: DataUploader) -> None:
        """Test parse_args method with log level argument."""
        mock_parse_args.return_value = MagicMock(log_level="DEBUG", config=None, db_connection_string=None, llm_model=None)
        data_uploader.logger = MagicMock()
        args = data_uploader.parse_args()
        assert args.log_level == "DEBUG"
        data_uploader.logger.setLevel.assert_called_once_with(logging.DEBUG)
        data_uploader.logger.debug.assert_called_once_with("Log level set to DEBUG")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config(self, mock_parse_args: MagicMock, data_uploader: DataUploader, tmp_path: Path) -> None:
        """Test parse_args method with config argument."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({"test": "config"}, f)
        mock_parse_args.return_value = MagicMock(log_level=None, config=str(config_file), db_connection_string=None, llm_model=None)
        data_uploader.logger = MagicMock()
        args = data_uploader.parse_args()
        assert args.config == str(config_file)
        assert data_uploader.config == {"test": "config"}
        data_uploader.logger.info.assert_called_once_with(f"Loaded configuration from {config_file}")

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(self, mock_parse_args: MagicMock, data_uploader: DataUploader, tmp_path: Path) -> None:
        """Test parse_args method with config argument when the file is not found."""
        config_file = tmp_path / "missing_config.yaml"
        mock_parse_args.return_value = MagicMock(log_level=None, config=str(config_file), db_connection_string=None, llm_model=None)
        data_uploader.logger = MagicMock()
        with pytest.raises(SystemExit) as exc_info:
            data_uploader.parse_args()
        assert exc_info.value.code == 1
        data_uploader.logger.error.assert_called_once_with(f"Configuration file not found: {config_file}")

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.core.data_upload.get_connection")
    def test_parse_args_db_connection_string(self, mock_get_connection: MagicMock, mock_parse_args: MagicMock, data_uploader: DataUploader) -> None:
        """Test parse_args method with db_connection_string argument."""
        mock_parse_args.return_value = MagicMock(log_level=None, config=None, db_connection_string="test_connection_string", llm_model=None)
        data_uploader.requires_db = True
        data_uploader.logger = MagicMock()
        args = data_uploader.parse_args()
        assert args.db_connection_string == "test_connection_string"
        mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
        assert data_uploader.db_conn == mock_get_connection.return_value
        data_uploader.logger.info.assert_called_once_with("Using custom database connection")

    @patch("argparse.ArgumentParser.parse_args")
    @patch("dewey.llm.llm_utils.get_llm_client")
    def test_parse_args_llm_model(self, mock_get_llm_client: MagicMock, mock_parse_args: MagicMock, data_uploader: DataUploader) -> None:
        """Test parse_args method with llm_model argument."""
        mock_parse_args.return_value = MagicMock(log_level=None, config=None, db_connection_string=None, llm_model="test_llm_model")
        data_uploader.enable_llm = True
        data_uploader.logger = MagicMock()
        args = data_uploader.parse_args()
        assert args.llm_model == "test_llm_model"
        mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
        assert data_uploader.llm_client == mock_get_llm_client.return_value
        data_uploader.logger.info.assert_called_once_with("Using custom LLM model: test_llm_model")
