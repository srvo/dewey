import pytest
from unittest.mock import MagicMock, patch
from dewey.core.utils.admin import AdminTasks
import logging
from dewey.core.base_script import BaseScript  # Import BaseScript

class TestAdminTasks:
    """Tests for the AdminTasks class."""

    @pytest.fixture
    def admin_tasks(self):
        """Fixture to create an AdminTasks instance with mocked dependencies."""
        with patch('dewey.core.utils.admin.BaseScript.__init__') as mock_base_init:
            mock_base_init.return_value = None  # Mock the base class __init__
            admin_tasks = AdminTasks()
            admin_tasks.logger = MagicMock(spec=logging.Logger)
            admin_tasks.db_conn = MagicMock()
            return admin_tasks

    def test_init(self, admin_tasks):
        """Test that AdminTasks initializes correctly."""
        # Assert that the base class __init__ was called with the correct arguments
        with patch('dewey.core.utils.admin.BaseScript.__init__') as mock_base_init:
            AdminTasks()
            mock_base_init.assert_called_once_with(config_section="admin", requires_db=True)

    def test_run(self, admin_tasks):
        """Test that run() executes the expected methods."""
        admin_tasks.perform_database_maintenance = MagicMock()
        admin_tasks.run()

        admin_tasks.logger.info.assert_called()
        admin_tasks.perform_database_maintenance.assert_called_once()

    def test_perform_database_maintenance_success(self, admin_tasks):
        """Test that perform_database_maintenance() executes SQL commands successfully."""
        mock_cursor = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = mock_cursor

        admin_tasks.perform_database_maintenance()

        admin_tasks.db_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_any_call("VACUUM;")
        mock_cursor.execute.assert_any_call("ANALYZE;")
        admin_tasks.db_conn.commit.assert_called_once()
        admin_tasks.logger.info.assert_called()

    def test_perform_database_maintenance_failure(self, admin_tasks):
        """Test that perform_database_maintenance() handles exceptions correctly."""
        admin_tasks.db_conn.cursor.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            admin_tasks.perform_database_maintenance()

        admin_tasks.logger.error.assert_called()
        admin_tasks.db_conn.commit.assert_not_called()

    def test_add_user_success(self, admin_tasks):
        """Test that add_user() executes SQL command successfully."""
        mock_cursor = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        username = "testuser"
        password = "testpassword"

        admin_tasks.add_user(username, password)

        admin_tasks.db_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO users (username, password) VALUES (%s, %s);",
            (username, password),
        )
        admin_tasks.db_conn.commit.assert_called_once()
        admin_tasks.logger.info.assert_called()

    def test_add_user_failure(self, admin_tasks):
        """Test that add_user() handles exceptions correctly."""
        admin_tasks.db_conn.cursor.side_effect = Exception("Database error")
        username = "testuser"
        password = "testpassword"

        with pytest.raises(Exception, match="Database error"):
            admin_tasks.add_user(username, password)

        admin_tasks.logger.error.assert_called()
        admin_tasks.db_conn.commit.assert_not_called()
