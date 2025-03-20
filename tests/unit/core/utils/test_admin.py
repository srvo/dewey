import pytest
from unittest.mock import MagicMock
from dewey.core.utils.admin import AdminTasks
import psycopg2

class TestAdminTasks:
    @pytest.fixture
    def admin_tasks(self):
        admin_tasks = AdminTasks()
        admin_tasks.db_conn = MagicMock()
        admin_tasks.logger = MagicMock()
        return admin_tasks

    def test_perform_database_maintenance_success(self, admin_tasks):
        cursor_mock = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = cursor_mock
        admin_tasks.perform_database_maintenance()
        cursor_mock.execute.assert_called_with("VACUUM;")
        cursor_mock.execute.assert_called_with("ANALYZE;")
        admin_tasks.db_conn.commit.assert_called_once()

    def test_perform_database_maintenance_failure(self, admin_tasks):
        cursor_mock = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = cursor_mock
        cursor_mock.execute.side_effect = psycopg2.Error("Test error")
        with pytest.raises(psycopg2.Error):
            admin_tasks.perform_database_maintenance()
        admin_tasks.db_conn.rollback.assert_called_once()

    def test_add_user_success(self, admin_tasks):
        cursor_mock = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = cursor_mock
        cursor_mock.fetchone.return_value = [False]  # Table and user don't exist
        admin_tasks.add_user("testuser", "testpassword")
        assert cursor_mock.execute.call_count == 4
        cursor_mock.execute.assert_any_call(
            "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users');"
        )
        cursor_mock.execute.assert_any_call(
            """
                        CREATE TABLE users (
                            username VARCHAR(255) PRIMARY KEY,
                            password VARCHAR(255)
                        );
                        """
        )
        cursor_mock.execute.assert_any_call(
            "SELECT EXISTS (SELECT 1 FROM users WHERE username = %s);", ("testuser",)
        )
        cursor_mock.execute.assert_any_call(
            "INSERT INTO users (username, password) VALUES (%s, %s);",
            ("testuser", "testpassword"),
        )
        admin_tasks.db_conn.commit.assert_called_once()

    def test_add_user_already_exists(self, admin_tasks):
        cursor_mock = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = cursor_mock
        cursor_mock.fetchone.side_effect = [[True], [True]]  # Table exists, user exists
        with pytest.raises(ValueError, match="User existinguser already exists."):
            admin_tasks.add_user("existinguser", "testpassword")
        admin_tasks.db_conn.commit.assert_not_called()
        admin_tasks.db_conn.rollback.assert_not_called()

    def test_add_user_database_error(self, admin_tasks):
        cursor_mock = MagicMock()
        admin_tasks.db_conn.cursor.return_value.__enter__.return_value = cursor_mock
        cursor_mock.execute.side_effect = psycopg2.Error("Test error")
        with pytest.raises(psycopg2.Error):
            admin_tasks.add_user("testuser", "testpassword")
        admin_tasks.db_conn.rollback.assert_called_once()
