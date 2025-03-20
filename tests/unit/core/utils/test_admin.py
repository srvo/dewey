import pytest
from unittest.mock import MagicMock
from dewey.core.utils.admin import AdminTasks
import psycopg2

@pytest.fixture
def mock_admin_tasks(mock_database_connection):
    admin_tasks = AdminTasks()
    admin_tasks.db_conn = mock_database_connection
    admin_tasks.logger = MagicMock()
    return admin_tasks

def test_perform_database_maintenance_success(mock_admin_tasks):
    mock_admin_tasks.perform_database_maintenance()
    mock_admin_tasks.db_conn.cursor.return_value.__enter__.return_value.execute.assert_called()
    mock_admin_tasks.db_conn.commit.assert_called_once()
    mock_admin_tasks.logger.info.assert_called()

def test_perform_database_maintenance_failure(mock_admin_tasks):
    mock_admin_tasks.db_conn.cursor.return_value.__enter__.return_value.execute.side_effect = psycopg2.Error("Test Error")
    with pytest.raises(psycopg2.Error):
        mock_admin_tasks.perform_database_maintenance()
    mock_admin_tasks.db_conn.rollback.assert_called_once()
    mock_admin_tasks.logger.error.assert_called()

def test_add_user_success(mock_admin_tasks):
    mock_admin_tasks.add_user("testuser", "testpassword")
    mock_admin_tasks.db_conn.cursor.return_value.__enter__.return_value.execute.assert_called()
    mock_admin_tasks.db_conn.commit.assert_called_once()
    mock_admin_tasks.logger.info.assert_called()

def test_add_user_already_exists(mock_admin_tasks):
    mock_admin_tasks.db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = [True]
    with pytest.raises(ValueError):
        mock_admin_tasks.add_user("existinguser", "testpassword")
    mock_admin_tasks.db_conn.rollback.assert_not_called()
    mock_admin_tasks.logger.error.assert_called()

def test_add_user_database_error(mock_admin_tasks):
    mock_admin_tasks.db_conn.cursor.return_value.__enter__.return_value.execute.side_effect = psycopg2.Error("Test Error")
    with pytest.raises(psycopg2.Error):
        mock_admin_tasks.add_user("testuser", "testpassword")
    mock_admin_tasks.db_conn.rollback.assert_called_once()
    mock_admin_tasks.logger.error.assert_called()

