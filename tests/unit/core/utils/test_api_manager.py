import logging

from dewey.core.utils.api_manager import ApiManager


def test_api_manager_run(caplog):
    """Test that ApiManager.run() logs the start and finish messages."""
    caplog.set_level(logging.INFO)
    api_manager = ApiManager()
    api_manager.run()
    assert "ApiManager started." in caplog.text
    assert "ApiManager finished." in caplog.text
