import logging
from unittest.mock import patch

import pytest

from dewey.core.utils.api_manager import ApiManager


class TestApiManager:
    """Unit tests for the ApiManager class."""

    @pytest.fixture
    def api_manager(self) -> ApiManager:
        """Fixture to create an instance of ApiManager."""
        return ApiManager()

    def test_initialization(self, api_manager: ApiManager) -> None:
        """Test that ApiManager initializes correctly."""
        assert api_manager.name == "ApiManager"
        assert api_manager.config_section == "api_manager"
        assert api_manager.logger is not None
        assert isinstance(api_manager.logger, logging.Logger)

    @patch("dewey.core.utils.api_manager.ApiManager.logger")
    def test_run_method(self, mock_logger, api_manager: ApiManager) -> None:
        """Test the run method of ApiManager."""
        api_manager.run()
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2

    @patch("dewey.core.utils.api_manager.BaseScript.__init__")
    def test_init_calls_basescript_init(self, mock_base_init):
        """Test that the ApiManager constructor calls the BaseScript constructor."""
        ApiManager()
        mock_base_init.assert_called_once_with(config_section="api_manager")
