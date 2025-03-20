import logging
from unittest.mock import MagicMock, patch
from typing import Any, Dict

import pytest
import yaml

from dewey.core.crm.labeler import LabelerModule
from dewey.core.base_script import BaseScript


class TestLabelerModule:
    """Tests for the LabelerModule class."""

    @pytest.fixture
    def labeler_module(self) -> LabelerModule:
        """Fixture for creating a LabelerModule instance."""
        return LabelerModule()

    def test_init(self, labeler_module: LabelerModule) -> None:
        """Test the __init__ method."""
        assert labeler_module.name == "LabelerModule"
        assert labeler_module.config_section == "labeler"
        assert labeler_module.logger is not None

    @patch("dewey.core.crm.labeler.llm_utils.get_llm_client")
    @patch("dewey.core.crm.labeler.DatabaseConnection")
    @patch("dewey.core.crm.labeler.BaseScript._load_config")
    @patch("dewey.core.crm.labeler.BaseScript._setup_logging")
    def test_init_with_dependencies(
        self, mock_setup_logging: MagicMock, mock_load_config: MagicMock, mock_database_connection: MagicMock, mock_llm_client: MagicMock, ) -> None:
        """Test the __init__ method with database and LLM dependencies."""
        mock_load_config.return_value=None, "llm": {}}
        labeler_module=None, enable_llm=True)

        assert labeler_module.db_conn is not None
        assert labeler_module.llm_client is not None
        mock_database_connection.assert_called_once()
        mock_llm_client.assert_called_once()

    @patch("dewey.core.crm.labeler.LabelerModule.get_config_value")
    def test_run_no_db_no_llm(self, mock_get_config_value: MagicMock, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when no database or LLM is available."""
        mock_get_config_value.return_value = "test_value"
        caplog.set_level(logging.INFO)

        labeler_module.run()

        assert "Labeler module started." in caplog.text
        assert "Some config value: test_value" in caplog.text
        assert "No database connection available." in caplog.text
        assert "No LLM client available." in caplog.text
        assert "Labeler module finished." in caplog.text

    @patch("dewey.core.crm.labeler.LabelerModule.get_config_value")
    def test_run_with_db_and_llm(self, mock_get_config_value: MagicMock, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when both database and LLM are available."""
        mock_get_config_value.return_value = "test_value"
        labeler_module.db_conn = MagicMock()
        labeler_module.llm_client = MagicMock()
        caplog.set_level(logging.INFO)

        labeler_module.run()

        assert "Labeler module started." in caplog.text
        assert "Some config value: test_value" in caplog.text
        assert "Database connection is available." in caplog.text
        assert "LLM client is available." in caplog.text
        assert "Labeler module finished." in caplog.text

    @patch("dewey.core.crm.labeler.LabelerModule.get_config_value")
    def test_run_exception(self, mock_get_config_value: MagicMock, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method when an exception is raised."""
        mock_get_config_value.side_effect = Exception("Test exception")
        caplog.set_level(logging.ERROR)

        with pytest.raises(Exception, match="Test exception"):
            if ) -> None:
        """Test the __init__ method with database and LLM dependencies."""
        mock_load_config.return_value is None:
                ) -> None:
        """Test the __init__ method with database and LLM dependencies."""
        mock_load_config.return_value = {"core": {"database": {}}
            if "llm": {}}
        labeler_module is None:
                "llm": {}}
        labeler_module = LabelerModule(requires_db=True
            labeler_module.run()

        assert "Error in labeler module: Test exception" in caplog.text

    def test_get_config_value(self, labeler_module: LabelerModule) -> None:
        """Test the get_config_value method."""
        labeler_module.config = {"key1": "value1", "key2": {"nested_key": "nested_value"}}

        assert labeler_module.get_config_value("key1") == "value1"
        assert labeler_module.get_config_value("key2.nested_key") == "nested_value"
        assert labeler_module.get_config_value("nonexistent_key", "default_value") == "default_value"
        assert labeler_module.get_config_value("key2.nonexistent_key", "default_value") == "default_value"

    @patch("dewey.core.crm.labeler.CONFIG_PATH", "nonexistent_config.yaml")
    def test_load_config_file_not_found(self, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test loading config when the file is not found."""
        caplog.set_level(logging.ERROR)
        with pytest.raises(FileNotFoundError):
            labeler_module._load_config()
        assert "Configuration file not found: nonexistent_config.yaml" in caplog.text

    @patch("dewey.core.crm.labeler.CONFIG_PATH", "invalid_config.yaml")
    def test_load_config_invalid_yaml(self, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory) -> None:
        """Test loading config when the YAML is invalid."""
        caplog.set_level(logging.ERROR)

        # Create a dummy invalid_config.yaml file
        invalid_config_path = tmp_path.join("invalid_config.yaml")
        invalid_config_path.write_text("key: value:\n  - item")

        with pytest.raises(yaml.YAMLError):
            labeler_module._load_config()
        assert "Error parsing YAML configuration" in caplog.text

    @patch("dewey.core.crm.labeler.CONFIG_PATH", "valid_config.yaml")
    def test_load_config_section(self, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory) -> None:
        """Test loading a specific config section."""
        caplog.set_level(logging.DEBUG)

        # Create a dummy valid_config.yaml file
        valid_config_path = tmp_path.join("valid_config.yaml")
        valid_config_path.write_text(yaml.dump({"section1": {"key1": "value1"}, "section2": {"key2": "value2"}}))

        labeler_module.config_section = "section1"
        config = labeler_module._load_config()
        assert config == {"key1": "value1"}
        assert "Loading configuration from valid_config.yaml" in caplog.text

    @patch("dewey.core.crm.labeler.CONFIG_PATH", "valid_config.yaml")
    def test_load_config_section_not_found(self, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory) -> None:
        """Test loading a config section that doesn't exist."""
        caplog.set_level(logging.WARNING)

        # Create a dummy valid_config.yaml file
        valid_config_path = tmp_path.join("valid_config.yaml")
        valid_config_path.write_text(yaml.dump({"section1": {"key1": "value1"}}))

        labeler_module.config_section = "section2"
        config = labeler_module._load_config()
        assert config == {"section1": {"key1": "value1"}}
        assert "Config section 'section2' not found in dewey.yaml. Using full config." in caplog.text

    @patch("dewey.core.crm.labeler.CONFIG_PATH", "valid_config.yaml")
    def test_load_config_no_section(self, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory) -> None:
        """Test loading the entire config without specifying a section."""
        caplog.set_level(logging.DEBUG)

        # Create a dummy valid_config.yaml file
        valid_config_path = tmp_path.join("valid_config.yaml")
        valid_config_path.write_text(yaml.dump({"section1": {"key1": "value1"}}))

        labeler_module.config_section = None
        config = labeler_module._load_config()
        assert config == {"section1": {"key1": "value1"}}
        assert "Loading configuration from valid_config.yaml" in caplog.text

    @patch("dewey.core.crm.labeler.logging.basicConfig")
    def test_setup_logging_from_config(self, mock_basicConfig: MagicMock, labeler_module: LabelerModule, tmp_path: pytest.TempPathFactory) -> None:
        """Test setting up logging from the config file."""
        # Create a dummy config file
        config_path = tmp_path.join("dewey.yaml")
        config_path.write_text(yaml.dump({"core": {"logging": {"level": "DEBUG", "format": "%(levelname)s - %(message)s", "date_format": "%Y-%m-%d"}}))

        with patch("dewey.core.crm.labeler.CONFIG_PATH", str(config_path)):
            labeler_module._setup_logging()

        mock_basicConfig.assert_called_once_with(
            level=logging.DEBUG,
            format="%(levelname)s - %(message)s",
            datefmt="%Y-%m-%d",
        )
        assert isinstance(labeler_module.logger, logging.Logger)

    @patch("dewey.core.crm.labeler.logging.basicConfig")
    def test_setup_logging_default(self, mock_basicConfig: MagicMock, labeler_module: LabelerModule, tmp_path: pytest.TempPathFactory) -> None:
        """Test setting up logging with default values."""
        # Create a dummy config file that doesn't contain logging config
        config_path=None, str(config_path)):
            if tmp_path: pytest.TempPathFactory) -> None:
        """Test setting up logging with default values."""
        # Create a dummy config file that doesn't contain logging config
        config_path is None:
                tmp_path: pytest.TempPathFactory) -> None:
        """Test setting up logging with default values."""
        # Create a dummy config file that doesn't contain logging config
        config_path = tmp_path.join("dewey.yaml")
        config_path.write_text(yaml.dump({"core": {}}))

        with patch("dewey.core.crm.labeler.CONFIG_PATH"
            labeler_module._setup_logging()

        mock_basicConfig.assert_called_once_with(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        assert isinstance(labeler_module.logger, logging.Logger)

    @patch("dewey.core.crm.labeler.logging.basicConfig")
    def test_setup_logging_no_config(self, mock_basicConfig: MagicMock, labeler_module: LabelerModule) -> None:
        """Test setting up logging when the config file is not found."""
        with patch("dewey.core.crm.labeler.CONFIG_PATH", "nonexistent_config.yaml"):
            labeler_module._setup_logging()

        mock_basicConfig.assert_called_once_with(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        assert isinstance(labeler_module.logger, logging.Logger)

    @patch("dewey.core.crm.labeler.get_connection")
    def test_initialize_db_connection_success(self, mock_get_connection: MagicMock, labeler_module: LabelerModule) -> None:
        """Test initializing the database connection successfully."""
        labeler_module.config = {"core": {"database": {"connection_string": "test_connection_string"}}}
        labeler_module._initialize_db_connection()
        assert labeler_module.db_conn is not None
        mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})

    def test_initialize_db_connection_import_error(self, labeler_module: LabelerModule) -> None:
        """Test initializing the database connection when the import fails."""
        with patch("dewey.core.crm.labeler.get_connection", side_effect=ImportError):
            with pytest.raises(ImportError):
                labeler_module._initialize_db_connection()
            assert labeler_module.db_conn is None

    @patch("dewey.core.crm.labeler.get_connection")
    def test_initialize_db_connection_exception(self, mock_get_connection: MagicMock, labeler_module: LabelerModule) -> None:
        """Test initializing the database connection when an exception is raised."""
        mock_get_connection.side_effect = Exception("Test exception")
        labeler_module.config = {"core": {"database": {"connection_string": "test_connection_string"}}}
        with pytest.raises(Exception, match="Test exception"):
            labeler_module._initialize_db_connection()
        assert labeler_module.db_conn is None

    @patch("dewey.core.crm.labeler.get_llm_client")
    def test_initialize_llm_client_success(self, mock_get_llm_client: MagicMock, labeler_module: LabelerModule) -> None:
        """Test initializing the LLM client successfully."""
        labeler_module.config = {"llm": {"model": "test_model"}}
        labeler_module._initialize_llm_client()
        assert labeler_module.llm_client is not None
        mock_get_llm_client.assert_called_once_with({"model": "test_model"})

    def test_initialize_llm_client_import_error(self, labeler_module: LabelerModule) -> None:
        """Test initializing the LLM client when the import fails."""
        with patch("dewey.core.crm.labeler.get_llm_client", side_effect=ImportError):
            with pytest.raises(ImportError):
                labeler_module._initialize_llm_client()
            assert labeler_module.llm_client is None

    @patch("dewey.core.crm.labeler.get_llm_client")
    def test_initialize_llm_client_exception(self, mock_get_llm_client: MagicMock, labeler_module: LabelerModule) -> None:
        """Test initializing the LLM client when an exception is raised."""
        mock_get_llm_client.side_effect = Exception("Test exception")
        labeler_module.config = {"llm": {"model": "test_model"}}
        with pytest.raises(Exception, match="Test exception"):
            labeler_module._initialize_llm_client()
        assert labeler_module.llm_client is None

    def test_setup_argparse(self, labeler_module: LabelerModule) -> None:
        """Test setting up the argument parser."""
        parser = labeler_module.setup_argparse()
        assert parser.description == labeler_module.description
        assert parser._actions[1].dest == "config"
        assert parser._actions[2].dest == "log_level"

    def test_setup_argparse_with_db_and_llm(self) -> None:
        """Test setting up the argument parser with database and LLM arguments."""
        labeler_module = LabelerModule(requires_db=True, enable_llm=True)
        parser = labeler_module.setup_argparse()
        assert parser._actions[1].dest == "config"
        assert parser._actions[2].dest == "log_level"
        assert parser._actions[3].dest == "db_connection_string"
        assert parser._actions[4].dest == "llm_model"

    @patch("dewey.core.crm.labeler.argparse.ArgumentParser.parse_args")
    def test_parse_args_log_level(self, mock_parse_args: MagicMock, labeler_module: LabelerModule) -> None:
        """Test parsing arguments and setting the log level."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch.object(labeler_module.logger, "setLevel") as mock_set_level:
            labeler_module.parse_args()
            mock_set_level.assert_called_once_with(logging.DEBUG)

    @patch("dewey.core.crm.labeler.argparse.ArgumentParser.parse_args")
    def test_parse_args_config(self, mock_parse_args: MagicMock, labeler_module: LabelerModule, tmp_path: pytest.TempPathFactory) -> None:
        """Test parsing arguments and loading the config file."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = str(tmp_path / "test_config.yaml")
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        config_data = {"test_key": "test_value"}
        with open(mock_args.config, "w") as f:
            yaml.dump(config_data, f)

        labeler_module.parse_args()
        assert labeler_module.config == config_data

    @patch("dewey.core.crm.labeler.argparse.ArgumentParser.parse_args")
    def test_parse_args_config_not_found(self, mock_parse_args: MagicMock, labeler_module: LabelerModule) -> None:
        """Test parsing arguments when the config file is not found."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = "nonexistent_config.yaml"
        mock_args.db_connection_string = None
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with pytest.raises(SystemExit) as exc_info:
            labeler_module.parse_args()
        assert exc_info.value.code == 1

    @patch("dewey.core.crm.labeler.argparse.ArgumentParser.parse_args")
    def test_parse_args_db_connection_string(self, mock_parse_args: MagicMock, labeler_module: LabelerModule) -> None:
        """Test parsing arguments and setting the database connection string."""
        labeler_module.requires_db = True
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = "test_db_connection_string"
        mock_args.llm_model = None
        mock_parse_args.return_value = mock_args

        with patch("dewey.core.crm.labeler.get_connection") as mock_get_connection:
            labeler_module.parse_args()
            mock_get_connection.assert_called_once_with({"connection_string": "test_db_connection_string"})
            assert labeler_module.db_conn is not None

    @patch("dewey.core.crm.labeler.argparse.ArgumentParser.parse_args")
    def test_parse_args_llm_model(self, mock_parse_args: MagicMock, labeler_module: LabelerModule) -> None:
        """Test parsing arguments and setting the LLM model."""
        labeler_module.enable_llm = True
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.config = None
        mock_args.db_connection_string = None
        mock_args.llm_model = "test_llm_model"
        mock_parse_args.return_value = mock_args

        with patch("dewey.core.crm.labeler.get_llm_client") as mock_get_llm_client:
            labeler_module.parse_args()
            mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
            assert labeler_module.llm_client is not None

    def test_execute_success(self, labeler_module: LabelerModule) -> None:
        """Test executing the script successfully."""
        with patch.object(labeler_module, "parse_args") as mock_parse_args, \
             patch.object(labeler_module, "run") as mock_run, \
             patch.object(labeler_module, "_cleanup") as mock_cleanup:
            mock_parse_args.return_value = MagicMock()
            labeler_module.execute()
            mock_parse_args.assert_called_once()
            mock_run.assert_called_once()
            mock_cleanup.assert_called_once()

    def test_execute_keyboard_interrupt(self, labeler_module: LabelerModule) -> None:
        """Test executing the script when a KeyboardInterrupt is raised."""
        with patch.object(labeler_module, "parse_args") as mock_parse_args, \
             patch.object(labeler_module, "run", side_effect=KeyboardInterrupt), \
             patch.object(labeler_module, "_cleanup") as mock_cleanup, \
             pytest.raises(SystemExit) as exc_info:
            mock_parse_args.return_value = MagicMock()
            labeler_module.execute()
            assert exc_info.value.code == 1
            mock_cleanup.assert_called_once()

    def test_execute_exception(self, labeler_module: LabelerModule) -> None:
        """Test executing the script when an exception is raised."""
        with patch.object(labeler_module, "parse_args") as mock_parse_args, \
             patch.object(labeler_module, "run", side_effect=Exception("Test exception")), \
             patch.object(labeler_module, "_cleanup") as mock_cleanup, \
             pytest.raises(SystemExit) as exc_info:
            mock_parse_args.return_value = MagicMock()
            labeler_module.execute()
            assert exc_info.value.code == 1
            mock_cleanup.assert_called_once()

    def test_cleanup(self, labeler_module: LabelerModule) -> None:
        """Test cleaning up resources."""
        labeler_module.db_conn = MagicMock()
        labeler_module._cleanup()
        labeler_module.db_conn.close.assert_called_once()

    def test_cleanup_no_db_conn(self, labeler_module: LabelerModule) -> None:
        """Test cleaning up resources when there is no database connection."""
        labeler_module.db_conn = None
        labeler_module._cleanup()

    def test_cleanup_db_conn_exception(self, labeler_module: LabelerModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test cleaning up resources when closing the database connection raises an exception."""
        caplog.set_level(logging.WARNING)
        db_conn = MagicMock()
        db_conn.close.side_effect = Exception("Test exception")
        labeler_module.db_conn = db_conn
        labeler_module._cleanup()
        assert "Error closing database connection: Test exception" in caplog.text

    def test_get_path_absolute(self, labeler_module: LabelerModule) -> None:
        """Test getting an absolute path."""
        absolute_path = "/absolute/path"
        assert labeler_module.get_path(absolute_path) == Path(absolute_path)

    def test_get_path_relative(self, labeler_module: LabelerModule) -> None:
        """Test getting a relative path."""
        relative_path = "relative/path"
        expected_path = labeler_module.PROJECT_ROOT / relative_path
        assert labeler_module.get_path(relative_path) == expected_path

    def test_base_script_inheritance(self, labeler_module: LabelerModule) -> None:
        """Test that LabelerModule inherits from BaseScript."""
        assert isinstance(labeler_module, BaseScript)
