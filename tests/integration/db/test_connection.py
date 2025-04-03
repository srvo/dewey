"""Tests for PostgreSQL database connection module.

This module tests the DatabaseConnection class and related functionality.
"""

import unittest
from unittest.mock import MagicMock, call, patch

from sqlalchemy import text

from src.dewey.core.db.connection import DatabaseConnection, DatabaseConnectionError


class TestDatabaseConnection(unittest.TestCase):
    """Test DatabaseConnection class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock SQLAlchemy components
        self.engine_patcher = patch("sqlalchemy.create_engine")
        self.mock_engine = self.engine_patcher.start()

        self.sessionmaker_patcher = patch("sqlalchemy.orm.sessionmaker")
        self.mock_sessionmaker = self.sessionmaker_patcher.start()

        self.scoped_session_patcher = patch("sqlalchemy.orm.scoped_session")
        self.mock_scoped_session = self.scoped_session_patcher.start()

        # Mock scheduler
        self.scheduler_patcher = patch(
            "apscheduler.schedulers.background.BackgroundScheduler"
        )
        self.mock_scheduler = self.scheduler_patcher.start()

        # Create mock objects
        self.mock_engine_instance = MagicMock()
        self.mock_engine.return_value = self.mock_engine_instance

        self.mock_session = MagicMock()
        self.mock_scoped_session.return_value = self.mock_session

        # Sample config
        self.config = {
            "postgres": {
                "host": "localhost",
                "port": 5432,
                "dbname": "test_db",
                "user": "test_user",
                "password": "test_pass",
                "sslmode": "prefer",
                "pool_min": 5,
                "pool_max": 10,
            }
        }

    def tearDown(self):
        """Tear down test fixtures."""
        self.engine_patcher.stop()
        self.sessionmaker_patcher.stop()
        self.scoped_session_patcher.stop()
        self.scheduler_patcher.stop()

    def test_init(self):
        """Test initialization with valid config."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Check engine was created with correct params
        self.mock_engine.assert_called_once()
        call_args = self.mock_engine.call_args[1]
        self.assertEqual(call_args["pool_size"], 5)
        self.assertEqual(call_args["max_overflow"], 10)
        self.assertTrue(call_args["pool_pre_ping"])

        # Check session factory was created
        self.mock_sessionmaker.assert_called_once_with(
            autocommit=False, autoflush=False, bind=self.mock_engine_instance
        )

        # Check scoped session was created
        self.mock_scoped_session.assert_called_once()

        # Check scheduler was started
        self.mock_scheduler.return_value.start.assert_called_once()

    def test_init_with_env_var(self):
        """Test initialization with DATABASE_URL environment variable."""
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql://env_user:env_pass@env_host:5432/env_db"},
        ):
            conn = DatabaseConnection(self.config)

            # Should use environment URL
            self.mock_engine.assert_called_once_with(
                "postgresql://env_user:env_pass@env_host:5432/env_db",
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )

    def test_validate_connection(self):
        """Test connection validation."""
        # Set up mock connection
        mock_conn = MagicMock()
        self.mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_conn
        )

        # Mock execute results
        mock_conn.execute.return_value.scalar.return_value = 1

        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Verify validation queries were executed
        mock_conn.execute.assert_has_calls(
            [
                call(text("SELECT 1")),
                call(text("SELECT MAX(version) FROM schema_versions")),
            ]
        )

    def test_validate_connection_failure(self):
        """Test connection validation failure."""
        # Set up mock to raise exception
        self.mock_engine_instance.connect.side_effect = Exception("Connection failed")

        with self.assertRaises(DatabaseConnectionError):
            DatabaseConnection(self.config)

    def test_get_session(self):
        """Test getting a session context manager."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Mock session behavior
        mock_session_instance = MagicMock()
        self.mock_scoped_session.return_value = mock_session_instance

        # Use session context
        with conn.get_session() as session:
            self.assertEqual(session, mock_session_instance)

        # Verify session was committed and closed
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.close.assert_called_once()

    def test_get_session_with_error(self):
        """Test session rollback on error."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Mock session behavior
        mock_session_instance = MagicMock()
        mock_session_instance.commit.side_effect = Exception("Test error")
        self.mock_scoped_session.return_value = mock_session_instance

        # Use session context with error
        with self.assertRaises(DatabaseConnectionError):
            with conn.get_session():
                pass

        # Verify rollback was called
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.close.assert_called_once()

    def test_close(self):
        """Test closing connection resources."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Close connection
        conn.close()

        # Verify resources were cleaned up
        self.mock_session.remove.assert_called_once()
        self.mock_engine_instance.dispose.assert_called_once()
        self.mock_scheduler.return_value.shutdown.assert_called_once_with(wait=False)


if __name__ == "__main__":
    unittest.main()