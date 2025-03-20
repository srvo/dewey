import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.searxng import SearxNG


class TestSearxNG:
    """
    Tests for the SearxNG class.
    """

    @pytest.fixture
    def searxng_instance(self) -> SearxNG:
        """
        Fixture to create a SearxNG instance.
        """
        return SearxNG()

    def test_init(self, searxng_instance: SearxNG) -> None:
        """
        Test the __init__ method.
        """
        assert searxng_instance.name == "SearxNG"
        assert searxng_instance.config_section == "searxng"
        assert searxng_instance.logger is not None

    @patch("dewey.core.engines.searxng.SearxNG.get_config_value")
    def test_run_success(
        self, mock_get_config_value: pytest.fixture, searxng_instance: SearxNG, caplog: pytest.fixture
    ) -> None:
        """
        Test the run method with successful execution.
        """
        mock_get_config_value.return_value = "http://localhost:8080"
        caplog.set_level(logging.INFO)

        searxng_instance.run()

        assert "Starting SearxNG script" in caplog.text
        assert "SearxNG API URL: http://localhost:8080" in caplog.text
        assert "SearxNG script completed" in caplog.text
        mock_get_config_value.assert_called_with("api_url", "http://localhost:8080")

    @patch("dewey.core.engines.searxng.SearxNG.get_config_value")
    def test_run_exception(
        self, mock_get_config_value: pytest.fixture, searxng_instance: SearxNG, caplog: pytest.fixture
    ) -> None:
        """
        Test the run method with an exception raised.
        """
        mock_get_config_value.side_effect = Exception("Test exception")
        caplog.set_level(logging.ERROR)

        with pytest.raises(Exception, match="Test exception"):
            searxng_instance.run()

        assert "Starting SearxNG script" in caplog.text
        assert "Error during SearxNG script execution: Test exception" in caplog.text
        mock_get_config_value.assert_called_with("api_url", "http://localhost:8080")
