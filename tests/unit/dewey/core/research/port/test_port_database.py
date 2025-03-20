import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.db.connection import DatabaseConnection
from dewey.core.research.port.port_database import PortDatabase


class TestPortDatabase:
    """Tests for the PortDatabase class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock = MagicMock()
        mock.config = {"database": {"url": "mock_url"}}
        mock.get_config_value.return_value = "mock_url"
        mock.logger = MagicMock()
        return mock

    @pytest.fixture
    def port_database(self, mock_base_script: MagicMock) -> PortDatabase:
        """Fixture to create a PortDatabase instance with a mocked BaseScript."""
        with patch(
            "dewey.core.research.port.port_database.BaseScript.__init__",
            return_value=None,
        ):
            port_db = PortDatabase()
            port_db.config = mock_base_script.config
            port_db.get_config_value = mock_base_script.get_config_value
            port_db.logger = mock_base_script.logger
        return port_db

    def test_init(self) -> None:
        """Test the __init__ method."""
        with patch(
            "dewey.core.research.port.port_database.BaseScript.__init__",
            return_value=None,
        ) as mock_init:
            port_db = PortDatabase()
            mock_init.assert_called_once_with(config_section="port_database")

    @patch("dewey.core.research.port.port_database.get_connection")
    def test_run_success(
        self, mock_get_connection: MagicMock, port_database: PortDatabase
    ) -> None:
        """Test the run method with a successful database connection."""
        mock_db_conn = MagicMock(spec=DatabaseConnection)
        mock_get_connection.return_value.__enter__.return_value = mock_db_conn

        port_database.run()

        port_database.logger.info.assert_any_call(
            "Starting Port Database operations."
        )
        port_database.logger.info.assert_any_call("Database URL: mock_url")
        mock_get_connection.assert_called_once_with(
            port_database.config.get("database", {})
        )
        port_database.logger.info.assert_any_call(
            "Successfully connected to the database."
        )
        port_database.logger.info.assert_any_call(
            "Port Database operations completed."
        )
        mock_db_conn.close.assert_not_called()

    @patch("dewey.core.research.port.port_database.get_connection")
    def test_run_non_database_connection(
        self, mock_get_connection: MagicMock, port_database: PortDatabase
    ) -> None:
        """Test the run method when the connection is not a DatabaseConnection instance."""
        mock_get_connection.return_value.__enter__.return_value = MagicMock()

        port_database.run()

        port_database.logger.warning.assert_called_once_with(
            "Database connection is not an instance of DatabaseConnection."
        )

    @patch("dewey.core.research.port.port_database.get_connection")
    def test_run_exception(
        self, mock_get_connection: MagicMock, port_database: PortDatabase
    ) -> None:
        """Test the run method when an exception occurs."""
        mock_get_connection.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            port_database.run()

        port_database.logger.error.assert_called_once()
        args, kwargs = port_database.logger.error.call_args
        assert "An error occurred: Test exception" in args[0]
        assert kwargs["exc_info"] is True

    @patch("dewey.core.research.port.port_database.get_connection")
    def test_run_database_operation(
        self, mock_get_connection: MagicMock, port_database: PortDatabase
    ) -> None:
        """Test the run method with a database operation."""
        mock_db_conn = MagicMock(spec=DatabaseConnection)
        mock_db_conn.con.table.return_value.limit.return_value.execute.return_value = [
            "result"
        ]
        mock_get_connection.return_value.__enter__.return_value = mock_db_conn

        port_database.run()

        mock_db_conn.con.table.assert_called_once_with("your_table")
        mock_db_conn.con.table.return_value.limit.assert_called_once_with(10)
        mock_db_conn.con.table.return_value.limit.return_value.execute.assert_called_once()
        port_database.logger.info.assert_any_call("Example query result: ['result']")
