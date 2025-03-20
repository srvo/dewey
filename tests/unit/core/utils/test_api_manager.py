import logging
from unittest.mock import patch
from dewey.core.utils.api_manager import ApiManager


def test_api_manager_run(caplog):
    """Test that ApiManager.run() executes and logs messages."""
    caplog.set_level(logging.INFO)
    api_manager = ApiManager()
    api_manager.run()
    assert "ApiManager started." in caplog.text
    assert "ApiManager finished." in caplog.text

