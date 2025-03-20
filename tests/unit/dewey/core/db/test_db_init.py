import logging
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.base_script import BaseScript
from dewey.core.db.db_init import DbInit


class TestDbInit:
    """Tests for the DbInit class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        with patch("dewey.core.db.db_init.BaseScript", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def mock_db_connection(self) -> MagicMock:
        """Mocks the DatabaseConnection class."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        return mock_conn

    @pytest.fixture
    def db_init(self, mock_base_script: MagicMock) -> DbInit:
        """Creates an instance of DbInit with mocked dependencies."""
        return DbInit()

    def test_init(self, mock_base_script: MagicMock) -> None:
        """Tests the __init__ method."""
        DbInit()
        mock_base_script.assert_called_once_with(
            config_section="db_init", requires_db=True
        )

    def test_run_success(
        self, db_init: DbInit, mock_db_connection: MagicMock
    ) -> None:
        """Tests the run method with a successful database initialization."""
        db_init.db_conn = mock_db_connection
        db_init.logger = MagicMock()
        db_init.get_config_value = MagicMock(return_value="test_host")

        db_init.run()

        db_init.logger.info.assert_any_call("Starting database initialization...")
        db_init.logger.info.assert_any_call("Database host: test_host")
        db_init.db_conn.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
            "SELECT 1;"
        )
        db_init.logger.info.assert_any_call("Database initialization complete.")

    def test_run_config_error(self, db_init: DbInit) -> None:
        """Tests the run method when there is an error getting the config value."""
        db_init.logger = MagicMock()
        db_init.get_config_value = MagicMock(side_effect=Exception("Config Error"))

        with pytest.raises(Exception, match="Config Error"):
            db_init.run()

        db_init.logger.info.assert_called_once_with(
            "Starting database initialization..."
        )
        db_init.logger.error.assert_called_once()

    def test_run_db_error(self, db_init: DbInit, mock_db_connection: MagicMock) -> None:
        """Tests the run method when there is an error during database initialization."""
        db_init.db_conn = mock_db_connection
        db_init.logger = MagicMock()
        db_init.get_config_value = MagicMock(return_value="test_host")
        db_init.db_conn.cursor.return_value.__enter__.return_value.execute.side_effect = (
            Exception("DB Error")
        )

        with pytest.raises(Exception, match="DB Error"):
            db_init.run()

        db_init.logger.info.assert_any_call("Starting database initialization...")
        db_init.logger.info.assert_any_call("Database host: test_host")
        db_init.db_conn.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
            "SELECT 1;"
        )
        db_init.logger.error.assert_called_once()

    @patch("dewey.core.db.db_init.DbInit.execute")
    def test_main(self, mock_execute: MagicMock) -> None:
        """Tests the main execution block."""
        with patch("dewey.core.db.db_init.DbInit") as mock_db_init:
            # Simulate the if __name__ == "__main__": block
            import dewey.core.db.db_init

            dewey.core.db.db_init.main()

            mock_db_init.assert_called_once()
            mock_execute.assert_called_once()
