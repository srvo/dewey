import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Mock PROJECT_ROOT and CONFIG_PATH for testing purposes
PROJECT_ROOT = Path("/tmp/test_dewey")
CONFIG_PATH = PROJECT_ROOT / "config" / "dewey.yaml"


# Create dummy config directory and file
@pytest.fixture(scope="session", autouse=True)
def setup_config():
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "dewey.yaml"
    default_config = {
        "core": {"logging": {"level": "INFO", "format": "%(message)s"}},
        "database": {"host": "localhost"},
        "llm": {"model": "test_model"},
    }
    with open(config_file, "w") as f:
        yaml.dump(default_config, f)
    yield
    # Teardown: Remove the dummy config directory and file
import shutil

    shutil.rmtree(PROJECT_ROOT)


# Mock load_dotenv
@pytest.fixture(autouse=True)
def mock_load_dotenv():
    with patch("dewey.core.base_script.load_dotenv") as mock:
        yield mock


# Mock get_connection
@pytest.fixture()
def mock_get_connection():
    with patch("dewey.core.base_script.get_connection") as mock:
        mock.return_value = MagicMock()
        yield mock


# Mock get_llm_client
@pytest.fixture()
def mock_get_llm_client():
    with patch("dewey.core.base_script.get_llm_client") as mock:
        mock.return_value = MagicMock()
        yield mock


# Fixture for DatabaseManager instance
@pytest.fixture()
def database_manager():
from dewey.core.db import DatabaseManager

    with patch("dewey.core.db.BaseScript.__init__", return_value=None):
        db_manager = DatabaseManager()
    return db_manager


# Fixture for BaseScript instance
@pytest.fixture()
def base_script():
from dewey.core.base_script import BaseScript

    with patch("dewey.core.base_script.load_dotenv"):
        bs = BaseScript()
    return bs


class TestDatabaseManager:
    """Unit tests for the DatabaseManager class."""

    def test_database_manager_initialization(self, database_manager):
        """Test that DatabaseManager initializes correctly."""
        assert database_manager.name == "DatabaseManager"
        assert database_manager.config_section == "database"
        assert database_manager.requires_db is True
        assert database_manager.enable_llm is True

    def test_database_manager_run_success(
        self, database_manager, mock_get_connection, caplog
    ):
        """Test the run method with a successful database connection."""
        database_manager.db_conn = MagicMock()
        caplog.set_level(logging.INFO)
        database_manager.run()
        assert "Starting database operations..." in caplog.text
        assert "Database host: localhost" in caplog.text
        assert "Successfully connected to the database." in caplog.text
        assert "Database operations completed." in caplog.text

    def test_database_manager_run_no_connection(self, database_manager, caplog):
        """Test the run method when the database connection is not established."""
        database_manager.db_conn = None
        caplog.set_level(logging.WARNING)
        database_manager.run()
        assert "Database connection not established." in caplog.text

    def test_database_manager_run_exception(self, database_manager, caplog):
        """Test the run method when an exception occurs."""
        database_manager.get_config_value = MagicMock(side_effect=Exception("Test Exception"))
        caplog.set_level(logging.ERROR)
        with pytest.raises(Exception, match="Test Exception"):
            database_manager.run()
        assert "An error occurred during database operations: Test Exception" in caplog.text


class TestBaseScript:
    """Unit tests for the BaseScript class."""

    def test_base_script_initialization(self, base_script):
        """Test that BaseScript initializes correctly."""
        assert base_script.name == "BaseScript"
        assert base_script.description is None
        assert base_script.config_section is None
        assert base_script.requires_db is False
        assert base_script.enable_llm is False
        assert isinstance(base_script.logger, logging.Logger)
        assert isinstance(base_script.config, dict)

    def test_base_script_initialization_with_params(self):
        """Test that BaseScript initializes correctly with parameters."""
from dewey.core.base_script import BaseScript

        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(
                name="TestScript",
                description="Test Description",
                config_section="test",
                requires_db=True,
                enable_llm=True,
            )
        assert bs.name == "TestScript"
        assert bs.description == "Test Description"
        assert bs.config_section == "test"
        assert bs.requires_db is True
        assert bs.enable_llm is True

    def test_setup_logging(self, base_script, caplog):
        """Test that setup_logging configures logging correctly."""
        caplog.set_level(logging.INFO)
        base_script._setup_logging()
        base_script.logger.info("Test log message")
        assert "Test log message" in caplog.text

    def test_load_config_success(self, base_script):
        """Test that load_config loads the configuration successfully."""
        config = base_script._load_config()
        assert isinstance(config, dict)
        assert "core" in config

    def test_load_config_section_success(self):
        """Test that load_config loads a specific configuration section successfully."""
from dewey.core.base_script import BaseScript

        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(config_section="database")
        config = bs._load_config()
        assert isinstance(config, dict)
        assert config == {"host": "localhost"}

    def test_load_config_section_not_found(self, caplog):
        """Test that load_config handles a missing configuration section."""
from dewey.core.base_script import BaseScript

        caplog.set_level(logging.WARNING)
        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(config_section="nonexistent")
        config = bs._load_config()
        assert "Config section 'nonexistent' not found in dewey.yaml. Using full config." in caplog.text
        assert isinstance(config, dict)
        assert "core" in config

    def test_load_config_file_not_found(self, base_script):
        """Test that load_config raises an exception when the configuration file is not found."""
        with patch("dewey.core.base_script.CONFIG_PATH", Path("nonexistent.yaml")), pytest.raises(
            FileNotFoundError
        ):
            base_script._load_config()

    def test_load_config_invalid_yaml(self, base_script):
        """Test that load_config raises an exception when the configuration file is invalid YAML."""
        invalid_yaml_path = PROJECT_ROOT / "config" / "invalid.yaml"
        with open(invalid_yaml_path, "w") as f:
            f.write("invalid: yaml: content")
        with patch("dewey.core.base_script.CONFIG_PATH", invalid_yaml_path), pytest.raises(yaml.YAMLError):
            base_script._load_config()

    def test_initialize_db_connection_success(self, base_script, mock_get_connection):
        """Test that initialize_db_connection initializes the database connection successfully."""
        base_script.config = {"core": {"database": {"test": "test"}}}
        base_script._initialize_db_connection()
        assert base_script.db_conn is not None
        mock_get_connection.assert_called_once_with({"test": "test"})

    def test_initialize_db_connection_import_error(self, base_script):
        """Test that initialize_db_connection handles an ImportError."""
        with patch("dewey.core.base_script.get_connection", side_effect=ImportError), pytest.raises(ImportError):
            base_script._initialize_db_connection()

    def test_initialize_db_connection_exception(self, base_script):
        """Test that initialize_db_connection handles a generic Exception."""
        with patch("dewey.core.base_script.get_connection", side_effect=Exception("Test Exception")), pytest.raises(
            Exception, match="Test Exception"
        ):
            base_script._initialize_db_connection()

    def test_initialize_llm_client_success(self, base_script, mock_get_llm_client):
        """Test that initialize_llm_client initializes the LLM client successfully."""
        base_script.config = {"llm": {"test": "test"}}
        base_script._initialize_llm_client()
        assert base_script.llm_client is not None
        mock_get_llm_client.assert_called_once_with({"test": "test"})

    def test_initialize_llm_client_import_error(self, base_script):
        """Test that initialize_llm_client handles an ImportError."""
        with patch("dewey.core.base_script.get_llm_client", side_effect=ImportError), pytest.raises(ImportError):
            base_script._initialize_llm_client()

    def test_initialize_llm_client_exception(self, base_script):
        """Test that initialize_llm_client handles a generic Exception."""
        with patch("dewey.core.base_script.get_llm_client", side_effect=Exception("Test Exception")), pytest.raises(
            Exception, match="Test Exception"
        ):
            base_script._initialize_llm_client()

    def test_setup_argparse(self, base_script):
        """Test that setup_argparse sets up the argument parser correctly."""
        parser = base_script.setup_argparse()
        assert parser.description is None
        assert parser._actions[1].dest == "config"
        assert parser._actions[2].dest == "log_level"

    def test_setup_argparse_with_db(self):
        """Test that setup_argparse adds database-specific arguments when requires_db is True."""
from dewey.core.base_script import BaseScript

        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(requires_db=True)
        parser = bs.setup_argparse()
        assert parser._actions[3].dest == "db_connection_string"

    def test_setup_argparse_with_llm(self):
        """Test that setup_argparse adds LLM-specific arguments when enable_llm is True."""
from dewey.core.base_script import BaseScript

        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(enable_llm=True)
        parser = bs.setup_argparse()
        assert parser._actions[3].dest == "llm_model"

    def test_parse_args(self, base_script, caplog):
        """Test that parse_args parses arguments correctly."""
        with patch.object(sys, "argv", ["script.py", "--log-level", "DEBUG"]):
            args = base_script.parse_args()
            assert args.log_level == "DEBUG"
            assert base_script.logger.level == logging.DEBUG

    def test_parse_args_config(self, base_script, caplog):
        """Test that parse_args loads config from file."""
        config_path = PROJECT_ROOT / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"test_key": "test_value"}, f)
        with patch.object(sys, "argv", ["script.py", "--config", str(config_path)]):
            args = base_script.parse_args()
            assert base_script.config["test_key"] == "test_value"
            assert f"Loaded configuration from {config_path}" in caplog.text

    def test_parse_args_config_not_found(self, base_script, caplog):
        """Test that parse_args handles config file not found."""
        with patch.object(sys, "argv", ["script.py", "--config", "nonexistent.yaml"]), pytest.raises(SystemExit):
            base_script.parse_args()
            assert "Configuration file not found: nonexistent.yaml" in caplog.text

    def test_parse_args_db_connection_string(self):
        """Test that parse_args updates db connection string."""
from dewey.core.base_script import BaseScript

        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(requires_db=True)
        with patch.object(sys, "argv", ["script.py", "--db-connection-string", "test_connection_string"]):
            with patch("dewey.core.base_script.get_connection") as mock_get_connection:
                bs.parse_args()
                mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})

    def test_parse_args_llm_model(self):
        """Test that parse_args updates llm model."""
from dewey.core.base_script import BaseScript

        with patch("dewey.core.base_script.load_dotenv"):
            bs = BaseScript(enable_llm=True)
        with patch.object(sys, "argv", ["script.py", "--llm-model", "test_llm_model"]):
            with patch("dewey.core.base_script.get_llm_client") as mock_get_llm_client:
                bs.parse_args()
                mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})

    def test_run_abstract(self, base_script):
        """Test that run is an abstract method."""
        with pytest.raises(TypeError):
            base_script.run()

    def test_execute_success(self, base_script, caplog):
        """Test that execute runs successfully."""
        base_script.run = MagicMock()
        caplog.set_level(logging.INFO)
        with patch.object(sys, "argv", ["script.py"]):
            base_script.execute()
            assert "Starting execution of BaseScript" in caplog.text
            base_script.run.assert_called_once()
            assert "Completed execution of BaseScript" in caplog.text

    def test_execute_keyboard_interrupt(self, base_script, caplog):
        """Test that execute handles KeyboardInterrupt."""
        base_script.run = MagicMock(side_effect=KeyboardInterrupt)
        caplog.set_level(logging.WARNING)
        with patch.object(sys, "argv", ["script.py"]), pytest.raises(SystemExit):
            base_script.execute()
            assert "Script interrupted by user" in caplog.text

    def test_execute_exception(self, base_script, caplog):
        """Test that execute handles a generic Exception."""
        base_script.run = MagicMock(side_effect=Exception("Test Exception"))
        caplog.set_level(logging.ERROR)
        with patch.object(sys, "argv", ["script.py"]), pytest.raises(SystemExit):
            base_script.execute()
            assert "Error executing script: Test Exception" in caplog.text

    def test_cleanup(self, base_script, caplog):
        """Test that cleanup closes the database connection."""
        base_script.db_conn = MagicMock()
        caplog.set_level(logging.DEBUG)
        base_script._cleanup()
        base_script.db_conn.close.assert_called_once()
        assert "Closing database connection" in caplog.text

    def test_cleanup_no_connection(self, base_script, caplog):
        """Test that cleanup handles no database connection."""
        base_script.db_conn = None
        caplog.set_level(logging.DEBUG)
        base_script._cleanup()
        assert "Closing database connection" not in caplog.text

    def test_cleanup_exception(self, base_script, caplog):
        """Test that cleanup handles an exception when closing the database connection."""
        base_script.db_conn = MagicMock()
        base_script.db_conn.close.side_effect = Exception("Test Exception")
        caplog.set_level(logging.WARNING)
        base_script._cleanup()
        assert "Error closing database connection: Test Exception" in caplog.text

    def test_get_path_absolute(self, base_script):
        """Test that get_path returns the path if it is absolute."""
        absolute_path = "/absolute/path"
        assert base_script.get_path(absolute_path) == Path(absolute_path)

    def test_get_path_relative(self, base_script):
        """Test that get_path returns the path relative to the project root."""
        relative_path = "relative/path"
        expected_path = PROJECT_ROOT / relative_path
        assert base_script.get_path(relative_path) == expected_path

    def test_get_config_value_success(self, base_script):
        """Test that get_config_value returns the correct value."""
        base_script.config = {"level1": {"level2": {"value": "test_value"}}}
        assert base_script.get_config_value("level1.level2.value") == "test_value"

    def test_get_config_value_default(self, base_script):
        """Test that get_config_value returns the default value if the key is not found."""
        base_script.config = {"level1": {"level2": {"value": "test_value"}}}
        assert base_script.get_config_value("level1.level2.nonexistent", "default_value") == "default_value"

    def test_get_config_value_missing_level(self, base_script):
        """Test that get_config_value returns the default value if a level is missing."""
        base_script.config = {"level1": {"level2": {"value": "test_value"}}}
        assert base_script.get_config_value("level1.nonexistent.value", "default_value") == "default_value"

    def test_get_config_value_no_default(self, base_script):
        """Test that get_config_value returns None if the key is not found and no default is provided."""
        base_script.config = {"level1": {"level2": {"value": "test_value"}}}
        assert base_script.get_config_value("level1.level2.nonexistent") is None
