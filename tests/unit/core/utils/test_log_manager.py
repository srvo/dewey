import pytest
from unittest.mock import patch
from dewey.core.utils.log_manager import LogManager


@pytest.fixture
def log_manager(mocker):
    """Fixture to create a LogManager instance for testing."""
    return LogManager()


@pytest.fixture
def mock_get_config_value(mocker):
    """Fixture to mock the get_config_value method."""
    return mocker.patch("dewey.core.utils.log_manager.LogManager.get_config_value")


def test_log_manager_initialization(log_manager):
    """Test that LogManager initializes without errors."""
    assert isinstance(log_manager, LogManager)


def test_get_log_level(log_manager, mock_get_config_value):
    """Test that get_log_level returns a string."""
    mock_get_config_value.return_value = "DEBUG"
    log_level = log_manager.get_log_level()
    assert isinstance(log_level, str)
    assert log_level == "DEBUG"


def test_get_log_file_path(log_manager, mock_get_config_value):
    """Test that get_log_file_path returns a string."""
    mock_get_config_value.return_value = "test.log"
    log_file_path = log_manager.get_log_file_path()
    assert isinstance(log_file_path, str)
    assert log_file_path == "test.log"


def test_some_other_function(log_manager, caplog, mock_get_config_value):
    """Test that some_other_function executes without errors and logs the expected message."""
    mock_get_config_value.return_value = "mocked_value"
    log_manager.some_other_function("test_arg")
    assert "Some value: mocked_value, Arg: test_arg" in caplog.text


def test_run(log_manager, caplog):
    """Test that the run method executes without errors and logs the expected message."""
    log_manager.run()
    assert "LogManager is running." in caplog.text


def test_execute(log_manager):
    """Test that execute method runs without errors."""
    log_manager.execute()
