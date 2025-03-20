import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml
from dotenv import load_dotenv

# Assuming the project root is two levels above the test file
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dewey.core.utils import MyUtils
from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm.llm_utils import call_llm


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture to provide a mock configuration dictionary."""
    return {
        "utils": {
            "example_config": "test_value",
            "database": {"connection_string": "test_db_url"},
            "llm": {"model": "test_llm_model"},
        },
        "core": {
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
            }
        },
    }


@pytest.fixture
def mock_base_script(mock_config: Dict[str, Any]) -> MagicMock:
    """Fixture to create a mock BaseScript instance."""
    with patch("dewey.core.base_script.load_dotenv"), patch(
        "dewey.core.base_script.yaml.safe_load", return_value=mock_config
    ), patch("dewey.core.base_script.logging.basicConfig"), patch(
        "dewey.core.base_script.logging.getLogger"
    ) as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        base_script = MagicMock(spec=BaseScript)
        base_script.name = "MockBaseScript"
        base_script.description = "Mock description"
        base_script.config_section = "utils"
        base_script.requires_db = True
        base_script.enable_llm = True
        base_script.config = mock_config["utils"]
        base_script.logger = mock_logger
        base_script.get_config_value.return_value = "default_value"
        yield base_script


@pytest.fixture
def my_utils_instance(mock_config: Dict[str, Any]) -> MyUtils:
    """Fixture to provide an instance of MyUtils with mocked dependencies."""
    with patch("dewey.core.utils.load_dotenv"), patch(
        "dewey.core.utils.yaml.safe_load", return_value=mock_config
    ), patch("dewey.core.utils.logging.basicConfig"), patch(
        "dewey.core.utils.logging.getLogger"
    ) as mock_get_logger, patch(
        "dewey.core.utils.get_connection"
    ) as mock_get_connection, patch(
        "dewey.core.utils.get_llm_client"
    ) as mock_get_llm_client:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_db_conn = MagicMock(spec=DatabaseConnection)
        mock_get_connection.return_value = mock_db_conn
        mock_llm_client = MagicMock()
        mock_get_llm_client.return_value = mock_llm_client

        utils = MyUtils()
        utils.logger = mock_logger
        utils.db_conn = mock_db_conn
        utils.llm_client = mock_llm_client
        yield utils


class TestMyUtils:
    """Tests for the MyUtils class."""

    def test_init(self, mock_config: Dict[str, Any]) -> None:
        """Test the __init__ method of MyUtils."""
        with patch("dewey.core.utils.load_dotenv"), patch(
            "dewey.core.utils.yaml.safe_load", return_value=mock_config
        ), patch("dewey.core.utils.logging.basicConfig"), patch(
            "dewey.core.utils.logging.getLogger"
        ) as mock_get_logger, patch(
            "dewey.core.utils.get_connection"
        ) as mock_get_connection, patch(
            "dewey.core.utils.get_llm_client"
        ) as mock_get_llm_client:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_db_conn = MagicMock(spec=DatabaseConnection)
            mock_get_connection.return_value = mock_db_conn
            mock_llm_client = MagicMock()
            mock_get_llm_client.return_value = mock_llm_client

            utils = MyUtils()

            assert utils.name == "MyUtils"
            assert utils.description == "Utility functions for Dewey project"
            assert utils.config_section == "utils"
            assert utils.requires_db is True
            assert utils.enable_llm is True
            mock_logger.info.assert_called_with("Initialized MyUtils")

    def test_run(self, my_utils_instance: MyUtils) -> None:
        """Test the run method of MyUtils."""
        with patch.object(my_utils_instance, "get_config_value", return_value="test_value"), patch.object(
            my_utils_instance.db_conn, "cursor"
        ) as mock_cursor, patch(
            "dewey.core.utils.call_llm", return_value="LLM response"
        ):
            mock_cursor.return_value.__enter__.return_value.execute.return_value = None
            mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)

            my_utils_instance.run()

            my_utils_instance.logger.info.assert_any_call("Starting utility functions...")
            my_utils_instance.logger.info.assert_any_call("Example config value: test_value")
            my_utils_instance.logger.info.assert_any_call(
                "Executing example database operation..."
            )
            my_utils_instance.logger.info.assert_any_call("Database query result: (1,)")
            my_utils_instance.logger.info.assert_any_call("Making example LLM call...")
            my_utils_instance.logger.info.assert_any_call("LLM response: LLM response")
            my_utils_instance.logger.info.assert_any_call("Utility functions completed.")

    def test_run_no_db(self, my_utils_instance: MyUtils) -> None:
        """Test the run method when the database connection is not available."""
        my_utils_instance.db_conn = None
        with patch.object(my_utils_instance, "get_config_value", return_value="test_value"), patch.object(
            my_utils_instance, "llm_client"
        ), patch("dewey.core.utils.call_llm", return_value="LLM response"):
            my_utils_instance.run()
            my_utils_instance.logger.warning.assert_called_with(
                "Database connection is not available."
            )

    def test_run_no_llm(self, my_utils_instance: MyUtils) -> None:
        """Test the run method when the LLM client is not available."""
        my_utils_instance.llm_client = None
        with patch.object(my_utils_instance, "get_config_value", return_value="test_value"), patch.object(
            my_utils_instance.db_conn, "cursor"
        ) as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.execute.return_value = None
            mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            my_utils_instance.run()
            my_utils_instance.logger.warning.assert_called_with("LLM client is not available.")

    def test_run_db_error(self, my_utils_instance: MyUtils) -> None:
        """Test the run method when a database error occurs."""
        with patch.object(my_utils_instance, "get_config_value", return_value="test_value"), patch.object(
            my_utils_instance.db_conn, "cursor"
        ) as mock_cursor, patch(
            "dewey.core.utils.call_llm", return_value="LLM response"
        ):
            mock_cursor.return_value.__enter__.return_value.execute.side_effect = Exception(
                "Database error"
            )
            my_utils_instance.run()
            my_utils_instance.logger.error.assert_called_with(
                "Error executing database query: Database error"
            )

    def test_run_llm_error(self, my_utils_instance: MyUtils) -> None:
        """Test the run method when an LLM error occurs."""
        with patch.object(my_utils_instance, "get_config_value", return_value="test_value"), patch.object(
            my_utils_instance.db_conn, "cursor"
        ) as mock_cursor, patch("dewey.core.utils.call_llm") as mock_call_llm:
            mock_cursor.return_value.__enter__.return_value.execute.return_value = None
            mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            mock_call_llm.side_effect = Exception("LLM error")
            my_utils_instance.run()
            my_utils_instance.logger.error.assert_called_with("Error calling LLM: LLM error")

    def test_run_general_error(self, my_utils_instance: MyUtils) -> None:
        """Test the run method when a general error occurs."""
        with patch.object(my_utils_instance, "get_config_value", side_effect=Exception("General error")):
            my_utils_instance.run()
            my_utils_instance.logger.error.assert_called_with(
                "An error occurred: General error", exc_info=True
            )

    def test_example_utility_function(self, my_utils_instance: MyUtils) -> None:
        """Test the example_utility_function method of MyUtils."""
        input_data = "test_input"
        expected_output = "Processed: test_input"
        actual_output = my_utils_instance.example_utility_function(input_data)
        assert actual_output == expected_output
        my_utils_instance.logger.info.assert_any_call(f"Processing input data: {input_data}")
        my_utils_instance.logger.info.assert_any_call(f"Output data: {expected_output}")
