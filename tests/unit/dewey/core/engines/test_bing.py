import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.bing import Bing


class TestBing:
    """
    Comprehensive unit tests for the Bing class.
    """

    @pytest.fixture
    def bing_engine(self):
        """
        Pytest fixture to create an instance of the Bing class.
        """
        return Bing()

    def test_init(self, bing_engine: Bing):
        """
        Test the initialization of the Bing class.
        """
        assert bing_engine.config_section == 'bing'
        assert bing_engine.name == 'Bing'
        assert bing_engine.logger is not None

    @patch("dewey.core.engines.bing.Bing.get_config_value")
    def test_run_api_key_present(self, mock_get_config_value, bing_engine: Bing, caplog):
        """
        Test the run method when the Bing API key is present in the config.
        """
        mock_get_config_value.return_value = "test_api_key"
        with caplog.at_level(logging.INFO):
            bing_engine.run()
        assert "Bing script started." in caplog.text
        assert "Bing script finished." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.engines.bing.Bing.get_config_value")
    def test_run_api_key_missing(self, mock_get_config_value, bing_engine: Bing, caplog):
        """
        Test the run method when the Bing API key is missing from the config.
        """
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.ERROR):
            bing_engine.run()
        assert "Bing script started." in caplog.text
        assert "Bing API key is not configured." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")
        assert "Bing script finished." not in caplog.text
