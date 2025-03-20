import logging
from unittest.mock import patch

import pytest
import yaml

from dewey.core.utils.log_manager import LogManager
from dewey.core.base_script import BaseScript


class TestLogManager:
    """Unit tests for the LogManager class."""

    @pytest.fixture
    def log_manager(self) -> LogManager:
        """Fixture to create a LogManager instance."""
        return LogManager()

    def test_init(self, log_manager: LogManager) -> None:
        """Test the __init__ method."""
        assert isinstance(log_manager, LogManager)
        assert isinstance(log_manager, BaseScript)
        assert log_manager.config_section == "log_manager"

    def test_run(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method."""
        caplog.set_level(logging.INFO)
        log_manager.run()
        assert "LogManager is running." in caplog.text

    def test_get_log_level(self, log_manager: LogManager) -> None:
        """Test the get_log_level method."""
        with patch.object(log_manager, "get_config_value", return_value="DEBUG"):
            log_level = log_manager.get_log_level()
            assert log_level == "DEBUG"

        with patch.object(log_manager, "get_config_value", return_value=None):
            log_level = log_manager.get_log_level()
            assert log_level == "INFO"

    def test_get_log_file_path(self, log_manager: LogManager) -> None:
        """Test the get_log_file_path method."""
        with patch.object(log_manager, "get_config_value", return_value="test.log"):
            log_file_path = log_manager.get_log_file_path()
            assert log_file_path == "test.log"

        with patch.object(log_manager, "get_config_value", return_value=None):
            log_file_path = log_manager.get_log_file_path()
            assert log_file_path == "application.log"

    def test_some_other_function(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the some_other_function method."""
        caplog.set_level(logging.INFO)
        with patch.object(log_manager, "get_config_value", return_value="test_value"):
            log_manager.some_other_function("test_arg")
            assert "Some value: test_value, Arg: test_arg" in caplog.text

    def test_execute(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method."""
        caplog.set_level(logging.INFO)
        with patch.object(log_manager, "parse_args") as mock_parse_args, \
             patch.object(log_manager, "run") as mock_run:
            mock_parse_args.return_value = None
            log_manager.execute()
            assert "Starting execution of LogManager" in caplog.text
            assert mock_run.called
            assert "Completed execution of LogManager" in caplog.text

    def test_execute_keyboard_interrupt(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method with KeyboardInterrupt."""
        caplog.set_level(logging.WARNING)
        with patch.object(log_manager, "parse_args") as mock_parse_args, \
             patch.object(log_manager, "run", side_effect=KeyboardInterrupt):
            mock_parse_args.return_value = None
            with pytest.raises(SystemExit) as exc_info:
                log_manager.execute()
            assert exc_info.value.code == 1
            assert "Script interrupted by user" in caplog.text

    def test_execute_exception(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method with an exception."""
        caplog.set_level(logging.ERROR)
        with patch.object(log_manager, "parse_args") as mock_parse_args, \
             patch.object(log_manager, "run", side_effect=ValueError("Test exception")):
            mock_parse_args.return_value = None
            with pytest.raises(SystemExit) as exc_info:
                log_manager.execute()
            assert exc_info.value.code == 1
            assert "Error executing script: Test exception" in caplog.text

    def test_cleanup(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _cleanup method."""
        caplog.set_level(logging.DEBUG)
        log_manager.db_conn = MockDBConnection()
        log_manager._cleanup()
        assert "Closing database connection" in caplog.text
        assert log_manager.db_conn.closed

        log_manager.db_conn = None
        log_manager._cleanup()  # Should not raise an exception

    def test_get_path(self, log_manager: LogManager) -> None:
        """Test the get_path method."""
        # Mock PROJECT_ROOT to ensure consistent test results
        with patch("dewey.core.utils.log_manager.PROJECT_ROOT", "/test/project"):
            # Test with relative path
            relative_path = "data/test.txt"
            expected_path = "/test/project/data/test.txt"
            assert str(log_manager.get_path(relative_path)) == expected_path

            # Test with absolute path
            absolute_path = "/absolute/path/test.txt"
            assert str(log_manager.get_path(absolute_path)) == absolute_path

    def test_get_config_value(self, log_manager: LogManager) -> None:
        """Test the get_config_value method."""
        log_manager.config = {"level1": {"level2": "value"}}

        # Test existing key
        assert log_manager.get_config_value("level1.level2") == "value"

        # Test non-existing key with default
        assert log_manager.get_config_value("level1.level3", default="default_value") == "default_value"

        # Test non-existing key without default
        assert log_manager.get_config_value("level1.level3") is None

        # Test non-existing top-level key
        assert log_manager.get_config_value("level4", default="default_value") == "default_value"

        # Test non-existing top-level key without default
        assert log_manager.get_config_value("level4") is None

    def test_setup_logging_from_config(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory) -> None:
        """Test that logging is configured from the config file."""
        caplog.set_level(logging.DEBUG)

        # Create a temporary config file with specific logging settings
        config_data = {
            'core': {
                'logging': {
                    'level': 'DEBUG',
                    'format': '%(levelname)s - %(message)s',
                    'date_format': '%Y-%m-%d',
                }
            }
        }
        config_file = tmp_path.mktemp("config") / "dewey.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Patch the CONFIG_PATH to point to the temporary config file
        with patch("dewey.core.utils.log_manager.CONFIG_PATH", config_file):
            # Initialize LogManager to trigger logging setup
            log_manager = LogManager()
            log_manager.logger.debug("Test message")

            # Assert that the log message is captured with the configured format and level
            assert "DEBUG - Test message" in caplog.text
            assert "%(asctime)s" not in caplog.text  # Check that the default format is overridden

    def test_setup_logging_default(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory) -> None:
        """Test that default logging is configured when config file is missing."""
        caplog.set_level(logging.INFO)

        # Create a temporary directory, but don't create the config file
        config_dir = tmp_path.mktemp("config")
        config_file = config_dir / "dewey.yaml"

        # Patch the CONFIG_PATH to point to the non-existent config file
        with patch("dewey.core.utils.log_manager.CONFIG_PATH", config_file):
            # Initialize LogManager to trigger logging setup
            log_manager = LogManager()
            log_manager.logger.info("Test message")

            # Assert that the log message is captured with the default format and level
            assert "INFO - dewey.core.utils.log_manager - Test message" in caplog.text
            assert "%(asctime)s" in caplog.text  # Check that the default format is used

    def test_parse_args_log_level(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the log level can be set via command line arguments."""
        monkeypatch.setattr("sys.argv", ["test_script.py", "--log-level", "DEBUG"])
        args = log_manager.parse_args()
        assert args.log_level == "DEBUG"
        assert log_manager.logger.level == logging.DEBUG
        caplog.set_level(logging.DEBUG)
        log_manager.logger.debug("Debug message")
        assert "Debug message" in caplog.text

    def test_parse_args_config_file(self, log_manager: LogManager, caplog: pytest.LogCaptureFixture, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the config file can be specified via command line arguments."""
        # Create a temporary config file with a specific value
        config_data = {'test_key': 'test_value'}
        config_file = tmp_path.mktemp("config") / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Set command line arguments to use the temporary config file
        monkeypatch.setattr("sys.argv", ["test_script.py", "--config", str(config_file)])

        # Parse arguments and check that the config is loaded correctly
        args = log_manager.parse_args()
        assert str(config_file) in str(args)
        assert log_manager.config['test_key'] == 'test_value'
        caplog.set_level(logging.INFO)
        log_manager.logger.info(f"Config loaded from {config_file}")
        assert f"Config loaded from {config_file}" in caplog.text

    def test_parse_args_config_file_not_found(self, log_manager: LogManager, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
        """Test that an error is raised if the specified config file does not exist."""
        # Set command line arguments to use a non-existent config file
        non_existent_config = tmp_path / "non_existent_config.yaml"
        monkeypatch.setattr("sys.argv", ["test_script.py", "--config", str(non_existent_config)])

        # Parse arguments and check that the script exits with an error
        with pytest.raises(SystemExit) as exc_info:
            log_manager.parse_args()
        assert exc_info.value.code == 1

    def test_parse_args_db_connection_string(self, log_manager: LogManager, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the database connection string can be set via command line arguments."""
        # Enable database requirement for the LogManager
        log_manager.requires_db = True

        # Set command line arguments to use a custom database connection string
        monkeypatch.setattr("sys.argv", ["test_script.py", "--db-connection-string", "test_connection_string"])

        # Mock the get_connection function to avoid actual database connection
        with patch("dewey.core.utils.log_manager.get_connection") as mock_get_connection:
            # Parse arguments and check that the custom connection string is used
            args = log_manager.parse_args()
            assert args.db_connection_string == "test_connection_string"
            mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})

    def test_parse_args_llm_model(self, log_manager: LogManager, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the LLM model can be set via command line arguments."""
        # Enable LLM requirement for the LogManager
        log_manager.enable_llm = True

        # Set command line arguments to use a custom LLM model
        monkeypatch.setattr("sys.argv", ["test_script.py", "--llm-model", "test_llm_model"])

        # Mock the get_llm_client function to avoid actual LLM client initialization
        with patch("dewey.core.utils.log_manager.get_llm_client") as mock_get_llm_client:
            # Parse arguments and check that the custom LLM model is used
            args = log_manager.parse_args()
            assert args.llm_model == "test_llm_model"
            mock_get_llm_client.assert_called_with({"model": "test_llm_model"})


class MockDBConnection:
    """Mock class for a database connection."""

    def __init__(self) -> None:
        """Initializes the mock connection."""
        self.closed = False

    def close(self) -> None:
        """Mocks closing the connection."""
        self.closed = True
