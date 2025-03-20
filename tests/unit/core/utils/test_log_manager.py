import pytest
from dewey.core.utils.log_manager import LogManager


@pytest.fixture
def log_manager():
    """Fixture to create a LogManager instance for testing."""
    return LogManager()


def test_log_manager_initialization(log_manager):
    """Test that LogManager initializes without errors."""
    assert isinstance(log_manager, LogManager)


def test_get_log_level(log_manager):
    """Test that get_log_level returns a string."""
    log_level = log_manager.get_log_level()
    assert isinstance(log_level, str)
    assert log_level in ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]  # Add possible log levels


def test_get_log_file_path(log_manager):
    """Test that get_log_file_path returns a string."""
    log_file_path = log_manager.get_log_file_path()
    assert isinstance(log_file_path, str)


def test_some_other_function(log_manager, caplog):
    """Test that some_other_function executes without errors and logs the expected message."""
    log_manager.some_other_function("test_arg")
    assert "Some value: default_value, Arg: test_arg" in caplog.text


def test_run(log_manager, caplog):
    """Test that the run method executes without errors and logs the expected message."""
    log_manager.run()
    assert "LogManager is running." in caplog.text

