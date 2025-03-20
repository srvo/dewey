import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.research.port import PortModule


class TestPortModule:
    """Tests for the PortModule class."""

    @pytest.fixture
    def mock_base_script(self):
        """Mocks the BaseScript class."""
        with patch("dewey.core.research.port.BaseScript.__init__") as mock:
            yield mock

    @pytest.fixture
    def port_module(self, mock_base_script):
        """Creates a PortModule instance with mocked dependencies."""
        mock_base_script.return_value = None  # Avoid calling BaseScript's init
        return PortModule(name="TestPort", description="A test port module")

    def test_init(self, mock_base_script):
        """Tests the __init__ method of PortModule."""
        PortModule(
            name="TestPort",
            description="A test port module",
            config_section="test_config",
            requires_db=True,
            enable_llm=True,
        )
        mock_base_script.assert_called_once_with(
            name="TestPort",
            description="A test port module",
            config_section="test_config",
            requires_db=True,
            enable_llm=True,
        )

    def test_run_no_dependencies(self, port_module, caplog):
        """Tests the run method with no database or LLM dependencies."""
        caplog.set_level(logging.INFO)
        port_module.logger = MagicMock()
        port_module.get_config_value = MagicMock(return_value="test_value")
        port_module.db_conn = None
        port_module.llm_client = None

        port_module.run()

        port_module.logger.info.assert_any_call("Running the port module...")
        port_module.logger.info.assert_any_call("Config value: test_value")

        assert "Database query result" not in caplog.text
        assert "LLM response" not in caplog.text

    def test_run_with_database(self, port_module, caplog):
        """Tests the run method with a mocked database connection."""
        caplog.set_level(logging.INFO)
        port_module.logger = MagicMock()
        port_module.get_config_value = MagicMock(return_value="test_value")
        port_module.llm_client = None

        # Mock database connection and cursor
        mock_db_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        port_module.db_conn = mock_db_conn

        port_module.run()

        port_module.logger.info.assert_any_call("Running the port module...")
        port_module.logger.info.assert_any_call("Config value: test_value")
        port_module.logger.info.assert_any_call("Database query result: [1]")

        assert "LLM response" not in caplog.text

    def test_run_with_database_error(self, port_module, caplog):
        """Tests the run method with a database error."""
        caplog.set_level(logging.ERROR)
        port_module.logger = MagicMock()
        port_module.get_config_value = MagicMock(return_value="test_value")
        port_module.llm_client = None

        # Mock database connection to raise an exception
        mock_db_conn = MagicMock()
        mock_db_conn.cursor.side_effect = Exception("Database error")
        port_module.db_conn = mock_db_conn

        port_module.run()

        port_module.logger.info.assert_any_call("Running the port module...")
        port_module.logger.info.assert_any_call("Config value: test_value")
        port_module.logger.error.assert_called_once()
        assert "Error executing database query" in caplog.text

        assert "LLM response" not in caplog.text

    def test_run_with_llm(self, port_module, caplog):
        """Tests the run method with a mocked LLM client."""
        caplog.set_level(logging.INFO)
        port_module.logger = MagicMock()
        port_module.get_config_value = MagicMock(return_value="test_value")
        port_module.db_conn = None

        # Mock LLM client
        mock_llm_client = MagicMock()
        mock_llm_client.generate.return_value = "A short poem."
        port_module.llm_client = mock_llm_client

        port_module.run()

        port_module.logger.info.assert_any_call("Running the port module...")
        port_module.logger.info.assert_any_call("Config value: test_value")
        port_module.logger.info.assert_any_call("LLM response: A short poem.")

        assert "Database query result" not in caplog.text

    def test_run_with_llm_error(self, port_module, caplog):
        """Tests the run method with an LLM error."""
        caplog.set_level(logging.ERROR)
        port_module.logger = MagicMock()
        port_module.get_config_value = MagicMock(return_value="test_value")
        port_module.db_conn = None

        # Mock LLM client to raise an exception
        mock_llm_client = MagicMock()
        mock_llm_client.generate.side_effect = Exception("LLM error")
        port_module.llm_client = mock_llm_client

        port_module.run()

        port_module.logger.info.assert_any_call("Running the port module...")
        port_module.logger.info.assert_any_call("Config value: test_value")
        port_module.logger.error.assert_called_once()
        assert "Error calling LLM" in caplog.text

        assert "Database query result" not in caplog.text

    def test_get_config_value(self, port_module):
        """Tests the get_config_value method."""
        port_module.config = {"test_key": "test_value"}
        value = port_module.get_config_value("test_key")
        assert value == "test_value"

        value = port_module.get_config_value("nonexistent_key", "default_value")
        assert value == "default_value"

        port_module.config = {"section": {"nested_key": "nested_value"}}
        value = port_module.get_config_value("section.nested_key")
        assert value == "nested_value"

        value = port_module.get_config_value("section.nonexistent_key", "default_value")
        assert value == "default_value"
