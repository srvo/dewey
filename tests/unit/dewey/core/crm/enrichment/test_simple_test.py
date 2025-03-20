import logging
from unittest.mock import patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.enrichment.simple_test import SimpleTest


class TestSimpleTest:
    """Unit tests for the SimpleTest module."""

    @pytest.fixture
    def simple_test(self) -> SimpleTest:
        """Fixture to create a SimpleTest instance."""
        return SimpleTest()

    def test_simple_test_initialization(self, simple_test: SimpleTest) -> None:
        """Test the initialization of the SimpleTest module."""
        assert simple_test.name == "SimpleTest"
        assert simple_test.description == "A simple test script for Dewey."
        assert isinstance(simple_test, BaseScript)
        assert simple_test.logger is not None

    @patch("dewey.core.crm.enrichment.simple_test.SimpleTest.get_config_value")
    def test_run_method(
        self, mock_get_config_value: pytest.fixture, simple_test: SimpleTest, caplog: pytest.fixture
    ) -> None:
        """Test the run method of the SimpleTest module."""
        mock_get_config_value.return_value = "test_value"
        caplog.set_level(logging.INFO)

        simple_test.run()

        assert "Starting SimpleTest module..." in caplog.text
        assert "Example config value: test_value" in caplog.text
        assert "SimpleTest module finished." in caplog.text
        mock_get_config_value.assert_called_with("example_config_key", "default_value")

    @patch("dewey.core.crm.enrichment.simple_test.SimpleTest.get_config_value")
    def test_run_method_with_default_config_value(
        self, mock_get_config_value: pytest.fixture, simple_test: SimpleTest, caplog: pytest.fixture
    ) -> None:
        """Test the run method when the config value is not found."""
        mock_get_config_value.return_value = None
        caplog.set_level(logging.INFO)

        simple_test.run()

        assert "Starting SimpleTest module..." in caplog.text
        assert "Example config value: default_value" in caplog.text
        assert "SimpleTest module finished." in caplog.text
        mock_get_config_value.assert_called_with("example_config_key", "default_value")
