import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.db.db_sync import DbSync


class TestDbSync:
    """Tests for the DbSync class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        mock = MagicMock(spec=BaseScript)
        mock.logger = MagicMock(spec=logging.Logger)
        mock.get_config_value.return_value = "test_value"
        mock.db_conn = MagicMock()
        return mock

    @pytest.fixture
    def db_sync(self, mock_base_script: MagicMock) -> DbSync:
        """Creates a DbSync instance with mocked dependencies."""
        with patch(
            "dewey.core.db.db_sync.BaseScript.__init__", return_value=None
        ):  # Mock the BaseScript init
            db_sync = DbSync()
            db_sync.logger = mock_base_script.logger
            db_sync.get_config_value = mock_base_script.get_config_value
            db_sync.db_conn = mock_base_script.db_conn
            return db_sync

    def test_init(self) -> None:
        """Tests the __init__ method."""
        with patch("dewey.core.db.db_sync.BaseScript.__init__") as mock_init:
            db_sync = DbSync()
            mock_init.assert_called_once_with(
                config_section="db_sync", requires_db=True
            )

    def test_run_success(self, db_sync: DbSync) -> None:
        """Tests the run method with successful database synchronization."""
        table_name = "test_table"
        db_sync.get_config_value.return_value = "test_db_url"
        db_sync.get_config_value.side_effect = [
            "test_db_url",
            table_name,
            table_name,
        ]  # Simulate config values
        db_sync.db_conn.execute.return_value = "query_result"

        with patch("dewey.core.db.utils.table_exists", return_value=True):
            db_sync.run()

        db_sync.logger.info.assert_any_call("Starting database synchronization...")
        db_sync.logger.info.assert_any_call("Using database URL: test_db_url")
        db_sync.logger.info.assert_any_call(f"Table '{table_name}' exists.")
        db_sync.logger.info.assert_any_call(
            f"Successfully executed query: SELECT * FROM {table_name} LIMIT 10"
        )
        db_sync.logger.debug.assert_called_with("Query result: query_result")
        db_sync.logger.info.assert_any_call("Database synchronization completed.")
        db_sync.db_conn.execute.assert_called_with(
            f"SELECT * FROM {table_name} LIMIT 10"
        )

    def test_run_table_not_exists(self, db_sync: DbSync) -> None:
        """Tests the run method when the table does not exist."""
        table_name = "test_table"
        db_sync.get_config_value.return_value = "test_db_url"
        db_sync.get_config_value.side_effect = [
            "test_db_url",
            table_name,
            table_name,
        ]  # Simulate config values

        with patch("dewey.core.db.utils.table_exists", return_value=False):
            db_sync.run()

        db_sync.logger.warning.assert_called_with(
            f"Table '{table_name}' does not exist."
        )

    def test_run_query_error(self, db_sync: DbSync) -> None:
        """Tests the run method when there is an error executing the query."""
        table_name = "test_table"
        db_sync.get_config_value.return_value = "test_db_url"
        db_sync.get_config_value.side_effect = [
            "test_db_url",
            table_name,
            table_name,
        ]  # Simulate config values
        db_sync.db_conn.execute.side_effect = Exception("query error")

        with patch("dewey.core.db.utils.table_exists", return_value=True):
            db_sync.run()

        db_sync.logger.error.assert_called_with("Error executing query: query error")

    def test_run_general_error(self, db_sync: DbSync) -> None:
        """Tests the run method when a general error occurs."""
        db_sync.get_config_value.side_effect = Exception("config error")

        with pytest.raises(Exception, match="config error"):
            db_sync.run()

        db_sync.logger.error.assert_called_with(
            "An error occurred during database synchronization: config error"
        )
