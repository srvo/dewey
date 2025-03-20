import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.apitube import Apitube


class TestApitube:
    """Unit tests for the Apitube class."""

    @pytest.fixture
    def apitube(self):
        """Fixture to create an Apitube instance."""
        return Apitube()

    def test_init(self, apitube):
        """Test the Apitube class initialization."""
        assert apitube.name == "Apitube"
        assert apitube.config_section == "apitube"
        assert apitube.logger is not None

    @patch("dewey.core.engines.apitube.Apitube.get_config_value")
    def test_run_success(self, mock_get_config_value, apitube, caplog):
        """Test the run method with a valid API key."""
        mock_get_config_value.return_value = "test_api_key"
        caplog.set_level(logging.INFO)
        apitube.run()
        assert "Starting Apitube script..." in caplog.text
        assert "API Key: test_api_key" in caplog.text
        assert "Apitube script completed." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.engines.apitube.Apitube.get_config_value")
    def test_run_no_api_key(self, mock_get_config_value, apitube, caplog):
        """Test the run method when the API key is missing."""
        mock_get_config_value.return_value = None
        caplog.set_level(logging.ERROR)
        apitube.run()
        assert "API key not found in configuration." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.engines.apitube.Apitube.get_config_value")
    def test_run_empty_api_key(self, mock_get_config_value, apitube, caplog):
        """Test the run method when the API key is an empty string."""
        mock_get_config_value.return_value = ""
        caplog.set_level(logging.ERROR)
        apitube.run()
        assert "API key not found in configuration." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")
