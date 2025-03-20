import pytest
from unittest.mock import MagicMock
from dewey.core.utils.api_manager import ApiManager
import logging


def test_api_manager_run():
    """Test that ApiManager.run() executes without errors."""
    mock_logger = MagicMock()
    api_manager = ApiManager(logger=mock_logger)
    api_manager.logger = mock_logger  # Directly assign the mock logger

    api_manager.run()

    mock_logger.info.assert_called()


def test_api_manager_initialization():
    """Test that ApiManager can be initialized without errors."""
    api_manager = ApiManager(logger=logging.getLogger(__name__))
    assert api_manager is not None
