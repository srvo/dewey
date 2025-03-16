"""Tests for main application module."""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management.base import CommandError


@pytest.mark.django_db
@patch("logging.config.dictConfig")
def test_setup_logging(mock_config) -> None:
    """Test logging setup."""
    from main import initialize_application

    with patch("main.create_database", return_value=0):
        initialize_application()
        mock_config.assert_called_once()


@pytest.mark.django_db
def test_create_database_success() -> None:
    """Test successful database creation."""
    # Import first
    from main import create_database

    # Then patch
    with (
        patch("main.call_command") as mock_call_command,
        patch("main.verify_database_schema", return_value=True) as mock_verify,
    ):
        result = create_database()
        assert result == 0
        mock_call_command.assert_called_once_with("migrate")
        mock_verify.assert_called_once()


@pytest.mark.django_db
@patch("main.verify_database_schema")
@patch("django.core.management.call_command")
def test_create_database_failure(mock_call_command, mock_verify) -> None:
    """Test database creation when verification fails."""
    from main import create_database

    mock_verify.side_effect = CommandError("Database error")
    with pytest.raises(CommandError) as exc_info:
        create_database()
    assert str(exc_info.value) == "Database error"


@pytest.mark.django_db
@patch("main.create_database")
def test_initialize_application(mock_create_db) -> None:
    """Test application initialization."""
    from main import initialize_application

    mock_create_db.return_value = 0
    result = initialize_application()
    assert result is True
    mock_create_db.assert_called_once()


@pytest.mark.django_db
@patch("main.create_database")
def test_initialize_application_failure(mock_create_db) -> None:
    """Test application initialization when database creation fails."""
    from main import initialize_application

    mock_create_db.side_effect = CommandError("Database error")
    result = initialize_application()
    assert result is False


@pytest.mark.django_db
def test_verify_database_schema() -> None:
    """Test database schema verification."""
    from main import verify_database_schema

    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance

        # Mock table existence check
        mock_cursor_instance.execute = MagicMock()
        mock_cursor_instance.fetchall.side_effect = [
            [("contacts",), ("emails",), ("email_contact_associations",)],  # Tables
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "email", "TEXT", 1, None, 0),
                (2, "created_at", "DATETIME", 1, None, 0),
            ],  # contacts columns
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "email_id", "INTEGER", 1, None, 1),
                (2, "contact_id", "INTEGER", 1, None, 1),
            ],  # email_contact_associations columns
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "gmail_id", "TEXT", 1, None, 0),
                (2, "subject", "TEXT", 1, None, 0),
                (3, "raw_content", "TEXT", 1, None, 0),
                (4, "received_at", "DATETIME", 1, None, 0),
                (5, "processed_at", "DATETIME", 1, None, 0),
            ],  # emails columns
        ]
        mock_cursor_instance.fetchone.side_effect = [(1,)]  # Gmail ID uniqueness check

        # Verify that the mock is called correctly
        result = verify_database_schema()
        assert result is True
        assert (
            mock_cursor_instance.execute.call_count == 5
        )  # 1 for tables, 1 for constraint, 3 for columns
        assert (
            mock_cursor_instance.fetchall.call_count == 4
        )  # 1 for tables, 3 for columns
        assert mock_cursor_instance.fetchone.call_count == 1  # 1 for constraint


@pytest.mark.django_db
def test_verify_database_schema_missing_table() -> None:
    """Test database schema verification when tables are missing."""
    from main import verify_database_schema

    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance

        # Mock missing tables
        mock_cursor_instance.fetchall.return_value = [("emails",)]

        with pytest.raises(CommandError) as exc_info:
            verify_database_schema()
        assert "Missing required tables" in str(exc_info.value)


@pytest.mark.django_db
def test_verify_database_schema_missing_columns() -> None:
    """Test database schema verification when columns are missing."""
    from main import verify_database_schema

    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance

        # Mock missing columns
        mock_cursor_instance.fetchall.side_effect = [
            [("contacts",), ("emails",), ("email_contact_associations",)],  # Tables
            [
                (0, "id", "INTEGER", 1, None, 1),
            ],  # Missing email and created_at columns in contacts
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "gmail_id", "TEXT", 1, None, 0),
            ],  # Missing columns in emails
            [
                (0, "email_id", "INTEGER", 1, None, 1),
            ],  # Missing contact_id in associations
            [(1,)],  # Gmail ID uniqueness check
        ]

        with pytest.raises(CommandError) as exc_info:
            verify_database_schema()
        assert "missing columns" in str(exc_info.value)


@pytest.mark.django_db
def test_verify_database_schema_invalid_constraint() -> None:
    """Test database schema verification when uniqueness constraint is missing."""
    from main import verify_database_schema

    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance

        # Mock table existence check
        mock_cursor_instance.execute = MagicMock()
        mock_cursor_instance.fetchall.side_effect = [
            [("contacts",), ("emails",), ("email_contact_associations",)],  # Tables
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "email", "TEXT", 1, None, 0),
                (2, "created_at", "DATETIME", 1, None, 0),
            ],  # contacts columns
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "gmail_id", "TEXT", 1, None, 0),
                (2, "subject", "TEXT", 1, None, 0),
                (3, "raw_content", "TEXT", 1, None, 0),
                (4, "received_at", "DATETIME", 1, None, 0),
                (5, "processed_at", "DATETIME", 1, None, 0),
            ],  # emails columns
            [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "email_id", "INTEGER", 1, None, 0),
                (2, "contact_id", "INTEGER", 1, None, 0),
            ],  # email_contact_associations columns
        ]
        mock_cursor_instance.fetchone.return_value = (0,)  # No uniqueness constraint

        with pytest.raises(CommandError) as exc_info:
            verify_database_schema()
        assert "Missing unique constraint" in str(exc_info.value)
