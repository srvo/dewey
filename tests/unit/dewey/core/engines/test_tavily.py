import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.tavily import Tavily
from dewey.core.base_script import BaseScript


class TestTavily:
    """Unit tests for the Tavily class."""

    @pytest.fixture
    def tavily_instance(self):
        """Fixture to create a Tavily instance."""
        return Tavily()

    def test_initialization(self, tavily_instance: Tavily):
        """Test that the Tavily class initializes correctly."""
        assert isinstance(tavily_instance, Tavily)
        assert isinstance(tavily_instance, BaseScript)
        assert tavily_instance.config_section == "tavily"

    @patch("dewey.core.engines.tavily.Tavily.get_config_value")
    def test_run_success(self, mock_get_config_value, tavily_instance: Tavily, caplog):
        """Test the run method with a successful API key retrieval."""
        mock_get_config_value.return_value = "test_api_key"
        with caplog.at_level(logging.INFO):
            tavily_instance.run()
        assert "Tavily API Key: test_api_key" in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.engines.tavily.Tavily.get_config_value")
    def test_run_no_api_key(
        self, mock_get_config_value, tavily_instance: Tavily, caplog
    ):
        """Test the run method when the API key is not configured."""
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.INFO):
            tavily_instance.run()
        mock_get_config_value.assert_called_once_with("api_key")
        # Optionally, assert that the code handles the missing API key gracefully,
        # e.g., by logging a warning or raising an exception.  The current code
        # does not do anything special.

    def test_get_config_value_existing_key(self, tavily_instance: Tavily):
        """Test get_config_value method with an existing key."""
        tavily_instance.config = {"tavily": {"api_key": "test_api_key"}}
        value = tavily_instance.get_config_value("tavily.api_key")
        assert value == "test_api_key"

    def test_get_config_value_nonexistent_key(self, tavily_instance: Tavily):
        """Test get_config_value method with a nonexistent key."""
        tavily_instance.config = {"tavily": {"api_key": "test_api_key"}}
        value = tavily_instance.get_config_value(
            "tavily.nonexistent_key", "default_value"
        )
        assert value == "default_value"

    def test_get_config_value_default_value(self, tavily_instance: Tavily):
        """Test get_config_value method with a default value."""
        tavily_instance.config = {}
        value = tavily_instance.get_config_value("tavily.api_key", "default_value")
        assert value == "default_value"
