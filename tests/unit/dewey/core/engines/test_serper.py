import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.serper import Serper


class TestSerper:
    """
    Unit tests for the Serper class.
    """

    @pytest.fixture
    def serper_instance(self):
        """
        Pytest fixture to create an instance of the Serper class.
        """
        return Serper()

    def test_init(self, serper_instance: Serper):
        """
        Test the initialization of the Serper class.
        """
        assert serper_instance.name == "Serper"
        assert serper_instance.config_section == "serper"
        assert serper_instance.logger is not None

    @patch("dewey.core.engines.serper.Serper.get_config_value")
    def test_run_success(self, mock_get_config_value, serper_instance: Serper, caplog):
        """
        Test the run method with a successful API key retrieval.
        """
        mock_get_config_value.return_value = "test_api_key"
        with caplog.at_level(logging.INFO):
            serper_instance.run()
        assert "Serper script running with API key: test_api_key" in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.engines.serper.Serper.get_config_value")
    def test_run_no_api_key(
        self, mock_get_config_value, serper_instance: Serper, caplog
    ):
        """
        Test the run method when the API key is not found in the configuration.
        """
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.INFO):
            serper_instance.run()
        mock_get_config_value.assert_called_once_with("api_key")
        # Depending on how you handle a missing API key, you might want to assert
        # that a warning or error is logged, or that the script exits gracefully.
        # For example, if you log a warning:
        # assert "API key not found in configuration." in caplog.text

    # Add more tests to cover specific Serper API interactions,
    # error handling, and edge cases as needed.
    # For example, you might want to test:
    # - Handling API errors (e.g., invalid API key, rate limiting)
    # - Parsing the API response
    # - Handling different types of search queries
    # - Caching search results
