import pytest
from dewey.core.utils.log_manager import LogManager


def test_log_manager_initialization():
    """Test that LogManager initializes without errors."""
    log_manager = LogManager()
    assert isinstance(log_manager, LogManager)


def test_log_manager_methods():
    """Test that LogManager methods can be called without errors."""
    log_manager = LogManager()
    log_level = log_manager.get_log_level()
    assert isinstance(log_level, str)

    log_file_path = log_manager.get_log_file_path()
    assert isinstance(log_file_path, str)

    log_manager.some_other_function("test_arg")

    # The run method should also execute without errors
    log_manager.run()
