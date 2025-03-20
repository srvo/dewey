import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.priority.priority_manager import PriorityManager


class TestPriorityManager:
    """Unit tests for the PriorityManager class."""

    @pytest.fixture
    def priority_manager(self) -> PriorityManager:
        """Fixture to create a PriorityManager instance with mocked dependencies."""
        with patch("dewey.core.crm.priority.priority_manager.DatabaseConnection"), patch(
            "dewey.core.crm.priority.priority_manager.get_connection"
        ), patch("dewey.core.crm.priority.priority_manager.get_motherduck_connection"):
            priority_manager = PriorityManager(requires_db=True, enable_llm=True)
            priority_manager.logger = MagicMock()  # Mock the logger
            priority_manager.db_conn = MagicMock()  # Mock the database connection
            priority_manager.llm_client = MagicMock()  # Mock the LLM client
            return priority_manager

    def test_init(self) -> None:
        """Test the initialization of the PriorityManager."""
        with patch("dewey.core.crm.priority.priority_manager.DatabaseConnection"), patch(
            "dewey.core.crm.priority.priority_manager.get_connection"
        ), patch("dewey.core.crm.priority.priority_manager.get_motherduck_connection"):
            priority_manager = PriorityManager(requires_db=True, enable_llm=True)
            assert priority_manager.name == "PriorityManager"
            assert priority_manager.description == "Manages priority within Dewey's CRM."
            assert priority_manager.config_section == "priority_manager"
            assert priority_manager.requires_db is True
            assert priority_manager.enable_llm is True

    def test_run_no_db_no_llm(self) -> None:
        """Test the run method when no database or LLM is available."""
        priority_manager = PriorityManager(requires_db=False, enable_llm=False)
        priority_manager.logger = MagicMock()
        priority_manager.db_conn = None
        priority_manager.llm_client = None
        priority_manager.get_config_value = MagicMock(return_value=0.75)

        priority_manager.run()

        priority_manager.logger.info.assert_called()
        priority_manager.logger.warning.assert_not_called()
        priority_manager.logger.error.assert_not_called()
        priority_manager.get_config_value.assert_called_with("priority_threshold", 0.5)

    def test_run_with_db_success(self, priority_manager: PriorityManager) -> None:
        """Test the run method with a successful database operation."""
        priority_manager.get_config_value = MagicMock(return_value=0.75)
        priority_manager.db_conn = MagicMock()
        priority_manager.llm_client = MagicMock()
        mock_execute_query = MagicMock(return_value="Success")
        with patch("dewey.core.crm.priority.priority_manager.execute_query", mock_execute_query):
            priority_manager.run()

        priority_manager.logger.info.assert_called()
        priority_manager.logger.warning.assert_not_called()
        priority_manager.logger.error.assert_not_called()
        mock_execute_query.assert_called()
        priority_manager.get_config_value.assert_called_with("priority_threshold", 0.5)

    def test_run_with_db_failure(self, priority_manager: PriorityManager) -> None:
        """Test the run method with a failed database operation."""
        priority_manager.get_config_value = MagicMock(return_value=0.75)
        priority_manager.db_conn = MagicMock()
        priority_manager.llm_client = MagicMock()
        mock_execute_query = MagicMock(side_effect=Exception("Database error"))
        with patch("dewey.core.crm.priority.priority_manager.execute_query", mock_execute_query):
            priority_manager.run()

        priority_manager.logger.info.assert_called()
        priority_manager.logger.warning.assert_not_called()
        priority_manager.logger.error.assert_called()
        mock_execute_query.assert_called()
        priority_manager.get_config_value.assert_called_with("priority_threshold", 0.5)

    def test_run_with_llm_success(self, priority_manager: PriorityManager) -> None:
        """Test the run method with a successful LLM operation."""
        priority_manager.get_config_value = MagicMock(return_value=0.75)
        priority_manager.db_conn = MagicMock()
        priority_manager.llm_client = MagicMock()
        mock_generate_text = MagicMock(return_value="LLM Summary")
        with patch("dewey.core.crm.priority.priority_manager.generate_text", mock_generate_text):
            priority_manager.run()

        priority_manager.logger.info.assert_called()
        priority_manager.logger.warning.assert_not_called()
        priority_manager.logger.error.assert_not_called()
        mock_generate_text.assert_called()
        priority_manager.get_config_value.assert_called_with("priority_threshold", 0.5)

    def test_run_with_llm_failure(self, priority_manager: PriorityManager) -> None:
        """Test the run method with a failed LLM operation."""
        priority_manager.get_config_value = MagicMock(return_value=0.75)
        priority_manager.db_conn = MagicMock()
        priority_manager.llm_client = MagicMock()
        mock_generate_text = MagicMock(side_effect=Exception("LLM error"))
        with patch("dewey.core.crm.priority.priority_manager.generate_text", mock_generate_text):
            priority_manager.run()

        priority_manager.logger.info.assert_called()
        priority_manager.logger.warning.assert_not_called()
        priority_manager.logger.error.assert_called()
        mock_generate_text.assert_called()
        priority_manager.get_config_value.assert_called_with("priority_threshold", 0.5)

    def test_run_no_db_connection(self, priority_manager: PriorityManager) -> None:
        """Test the run method when no database connection is available."""
        priority_manager.db_conn = None
        priority_manager.llm_client = MagicMock()
        priority_manager.get_config_value = MagicMock(return_value=0.75)

        priority_manager.run()

        priority_manager.logger.warning.assert_called_with("No database connection available.")

    def test_run_no_llm_client(self, priority_manager: PriorityManager) -> None:
        """Test the run method when no LLM client is available."""
        priority_manager.db_conn = MagicMock()
        priority_manager.llm_client = None
        priority_manager.get_config_value = MagicMock(return_value=0.75)

        priority_manager.run()

        priority_manager.logger.warning.assert_called_with("No LLM client available.")

    def test_config_value_retrieval(self, priority_manager: PriorityManager) -> None:
        """Test the retrieval of configuration values."""
        priority_manager.config = {"section": {"key": "value"}}
        assert priority_manager.get_config_value("section.key") == "value"
        assert priority_manager.get_config_value("section.missing_key", "default") == "default"
        assert priority_manager.get_config_value("missing_section.key", "default") == "default"
        assert priority_manager.get_config_value("missing_section", "default") == "default"
        assert priority_manager.get_config_value("section.key") == "value"

    def test_config_value_retrieval_no_default(self, priority_manager: PriorityManager) -> None:
        """Test the retrieval of configuration values without a default value."""
        priority_manager.config = {"section": {"key": "value"}}
        assert priority_manager.get_config_value("section.key") == "value"
        assert priority_manager.get_config_value("section.missing_key") is None
        assert priority_manager.get_config_value("missing_section.key") is None
        assert priority_manager.get_config_value("missing_section") is None

    def test_get_path_absolute(self, priority_manager: PriorityManager) -> None:
        """Test get_path with an absolute path."""
        absolute_path = "/absolute/path"
        assert priority_manager.get_path(absolute_path) == absolute_path

    def test_get_path_relative(self, priority_manager: PriorityManager) -> None:
        """Test get_path with a relative path."""
        relative_path = "relative/path"
        expected_path = priority_manager.PROJECT_ROOT / relative_path
        assert priority_manager.get_path(relative_path) == expected_path

    def test_setup_logging_from_config(self, priority_manager: PriorityManager) -> None:
        """Test setup_logging with configuration."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
core:
  logging:
    level: DEBUG
    format: '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    date_format: '%Y-%m-%d %H:%M:%S'
"""
            priority_manager._setup_logging()
            assert priority_manager.logger.level == logging.DEBUG

    def test_setup_logging_default(self, priority_manager: PriorityManager) -> None:
        """Test setup_logging with default configuration."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.side_effect = FileNotFoundError
            priority_manager._setup_logging()
            assert priority_manager.logger.level == logging.INFO

    def test_load_config_success(self, priority_manager: PriorityManager) -> None:
        """Test loading configuration successfully."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
section1:
  key1: value1
section2:
  key2: value2
"""
            priority_manager.config_section = "section1"
            config = priority_manager._load_config()
            assert config == {"key1": "value1"}

    def test_load_config_no_section(self, priority_manager: PriorityManager) -> None:
        """Test loading configuration with no specific section."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
section1:
  key1: value1
section2:
  key2: value2
"""
            priority_manager.config_section = None
            config = priority_manager._load_config()
            assert config == {"section1": {"key1": "value1"}, "section2": {"key2": "value2"}}

    def test_load_config_section_not_found(self, priority_manager: PriorityManager) -> None:
        """Test loading configuration when the specified section is not found."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
section1:
  key1: value1
section2:
  key2: value2
"""
            priority_manager.config_section = "missing_section"
            config = priority_manager._load_config()
            assert config == {"section1": {"key1": "value1"}, "section2": {"key2": "value2"}}

    def test_load_config_file_not_found(self, priority_manager: PriorityManager) -> None:
        """Test loading configuration when the file is not found."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.side_effect = FileNotFoundError
            with pytest.raises(FileNotFoundError):
                priority_manager._load_config()

    def test_load_config_yaml_error(self, priority_manager: PriorityManager) -> None:
        """Test loading configuration when there is a YAML error."""
        with patch("dewey.core.crm.priority.priority_manager.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "invalid yaml"
            with pytest.raises(Exception):
                priority_manager._load_config()

    def test_initialize_db_connection_success(self, priority_manager: PriorityManager) -> None:
        """Test initializing the database connection successfully."""
        with patch("dewey.core.crm.priority.priority_manager.get_connection") as mock_get_connection:
            priority_manager.config = {"core": {"database": {"db_url": "test_url"}}}
            priority_manager._initialize_db_connection()
            assert priority_manager.db_conn is not None
            mock_get_connection.assert_called_once()

    def test_initialize_db_connection_import_error(self, priority_manager: PriorityManager) -> None:
        """Test initializing the database connection when there is an import error."""
        with patch("dewey.core.crm.priority.priority_manager.get_connection") as mock_get_connection:
            mock_get_connection.side_effect = ImportError
            with pytest.raises(ImportError):
                priority_manager._initialize_db_connection()
            assert priority_manager.db_conn is None

    def test_initialize_db_connection_exception(self, priority_manager: PriorityManager) -> None:
        """Test initializing the database connection when there is an exception."""
        with patch("dewey.core.crm.priority.priority_manager.get_connection") as mock_get_connection:
            mock_get_connection.side_effect = Exception("Connection failed")
            with pytest.raises(Exception):
                priority_manager._initialize_db_connection()
            assert priority_manager.db_conn is None

    def test_initialize_llm_client_success(self, priority_manager: PriorityManager) -> None:
        """Test initializing the LLM client successfully."""
        with patch("dewey.core.crm.priority.priority_manager.get_llm_client") as mock_get_llm_client:
            priority_manager.config = {"llm": {"model": "test_model"}}
            priority_manager._initialize_llm_client()
            assert priority_manager.llm_client is not None
            mock_get_llm_client.assert_called_once()

    def test_initialize_llm_client_import_error(self, priority_manager: PriorityManager) -> None:
        """Test initializing the LLM client when there is an import error."""
        with patch("dewey.core.crm.priority.priority_manager.get_llm_client") as mock_get_llm_client:
            mock_get_llm_client.side_effect = ImportError
            with pytest.raises(ImportError):
                priority_manager._initialize_llm_client()
            assert priority_manager.llm_client is None

    def test_initialize_llm_client_exception(self, priority_manager: PriorityManager) -> None:
        """Test initializing the LLM client when there is an exception."""
        with patch("dewey.core.crm.priority.priority_manager.get_llm_client") as mock_get_llm_client:
            mock_get_llm_client.side_effect = Exception("Client failed")
            with pytest.raises(Exception):
                priority_manager._initialize_llm_client()
            assert priority_manager.llm_client is None

    def test_cleanup_db_connection(self, priority_manager: PriorityManager) -> None:
        """Test cleaning up the database connection."""
        priority_manager.db_conn = MagicMock()
        priority_manager._cleanup()
        priority_manager.db_conn.close.assert_called_once()

    def test_cleanup_no_db_connection(self, priority_manager: PriorityManager) -> None:
        """Test cleaning up when there is no database connection."""
        priority_manager.db_conn = None
        priority_manager._cleanup()

    def test_cleanup_db_connection_error(self, priority_manager: PriorityManager) -> None:
        """Test cleaning up the database connection when there is an error."""
        priority_manager.db_conn = MagicMock()
        priority_manager.db_conn.close.side_effect = Exception("Close failed")
        priority_manager._cleanup()
        priority_manager.logger.warning.assert_called()

    def test_setup_argparse(self, priority_manager: PriorityManager) -> None:
        """Test setting up the argument parser."""
        parser = priority_manager.setup_argparse()
        assert parser is not None
        assert parser.description == priority_manager.description

    def test_parse_args_log_level(self, priority_manager: PriorityManager) -> None:
        """Test parsing arguments with a log level."""
        with patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(log_level="DEBUG")):
            args = priority_manager.parse_args()
            assert args.log_level == "DEBUG"

    def test_parse_args_config(self, priority_manager: PriorityManager) -> None:
        """Test parsing arguments with a config file."""
        with patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(config="test_config.yaml")), patch(
            "dewey.core.crm.priority.priority_manager.open", create=True
        ) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
section1:
  key1: value1
"""
            args = priority_manager.parse_args()
            assert args.config == "test_config.yaml"
            assert priority_manager.config == {"section1": {"key1": "value1"}}

    def test_parse_args_config_not_found(self, priority_manager: PriorityManager) -> None:
        """Test parsing arguments with a config file that is not found."""
        with patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(config="test_config.yaml")), patch(
            "dewey.core.crm.priority.priority_manager.open", create=True
        ) as mock_open, pytest.raises(SystemExit) as exc_info:
            mock_open.side_effect = FileNotFoundError
            priority_manager.parse_args()
            assert exc_info.value.code == 1

    def test_parse_args_db_connection_string(self, priority_manager: PriorityManager) -> None:
        """Test parsing arguments with a database connection string."""
        with patch(
            "argparse.ArgumentParser.parse_args", return_value=MagicMock(db_connection_string="test_connection_string")
        ), patch("dewey.core.crm.priority.priority_manager.get_connection") as mock_get_connection:
            args = priority_manager.parse_args()
            assert args.db_connection_string == "test_connection_string"
            mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})

    def test_parse_args_llm_model(self, priority_manager: PriorityManager) -> None:
        """Test parsing arguments with an LLM model."""
        with patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(llm_model="test_llm_model")), patch(
            "dewey.core.crm.priority.priority_manager.get_llm_client"
        ) as mock_get_llm_client:
            args = priority_manager.parse_args()
            assert args.llm_model == "test_llm_model"
            mock_get_llm_client.assert_called_with({"model": "test_llm_model"})

    def test_execute_success(self, priority_manager: PriorityManager) -> None:
        """Test executing the script successfully."""
        with patch("dewey.core.crm.priority.priority_manager.PriorityManager.parse_args", return_value=MagicMock()), patch(
            "dewey.core.crm.priority.priority_manager.PriorityManager.run"
        ) as mock_run, patch("dewey.core.crm.priority.priority_manager.PriorityManager._cleanup") as mock_cleanup:
            priority_manager.execute()
            mock_run.assert_called_once()
            mock_cleanup.assert_called_once()

    def test_execute_keyboard_interrupt(self, priority_manager: PriorityManager) -> None:
        """Test executing the script with a keyboard interrupt."""
        with patch("dewey.core.crm.priority.priority_manager.PriorityManager.parse_args", return_value=MagicMock()), patch(
            "dewey.core.crm.priority.priority_manager.PriorityManager.run", side_effect=KeyboardInterrupt
        ), patch("dewey.core.crm.priority.priority_manager.PriorityManager._cleanup") as mock_cleanup, pytest.raises(
            SystemExit
        ) as exc_info:
            priority_manager.execute()
            assert exc_info.value.code == 1
            mock_cleanup.assert_called_once()

    def test_execute_exception(self, priority_manager: PriorityManager) -> None:
        """Test executing the script with an exception."""
        with patch("dewey.core.crm.priority.priority_manager.PriorityManager.parse_args", return_value=MagicMock()), patch(
            "dewey.core.crm.priority.priority_manager.PriorityManager.run", side_effect=Exception("Test exception")
        ), patch("dewey.core.crm.priority.priority_manager.PriorityManager._cleanup") as mock_cleanup, pytest.raises(
            SystemExit
        ) as exc_info:
            priority_manager.execute()
            assert exc_info.value.code == 1
            mock_cleanup.assert_called_once()
