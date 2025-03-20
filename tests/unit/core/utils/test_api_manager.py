import pytest
from unittest.mock import MagicMock
from dewey.core.utils.api_manager import ApiManager


def test_api_manager_run(mocker):
    """Test that ApiManager.run() executes without errors."""
    mock_logger = MagicMock()
    api_manager = ApiManager()
    api_manager.logger = mock_logger  # Directly assign the mock logger

    api_manager.run()

    mock_logger.info.assert_called()
