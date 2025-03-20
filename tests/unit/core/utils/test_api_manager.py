import logging

from dewey.core.utils.api_manager import ApiManager


def test_api_manager_initialization():
    """Test that ApiManager can be initialized without errors."""
    api_manager = ApiManager()
    assert isinstance(api_manager, ApiManager)


def test_api_manager_run_method(caplog):
    """Test that the run method executes without errors and logs messages."""
    caplog.set_level(logging.INFO)
    api_manager = ApiManager()
    api_manager.run()
    assert "ApiManager started." in caplog.text
    assert "ApiManager finished." in caplog.text
