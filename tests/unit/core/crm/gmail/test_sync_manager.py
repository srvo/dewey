"""Tests for the Gmail sync manager."""

import pytest
from unittest.mock import patch, MagicMock
import duckdb
from dewey.core.crm.gmail.gmail_sync_manager import GmailSyncManager


def test_sync_manager_init(temp_db_path):
    """Test GmailSyncManager initialization."""
    manager = GmailSyncManager(
        db_path=temp_db_path,
        motherduck_db="test_db",
        batch_size=50,
        max_retries=3,
        retry_delay=1,
    )

    assert str(manager.db_path) == str(temp_db_path)
    assert manager.motherduck_db == "test_db"
    assert manager.batch_size == 50
    assert manager.max_retries == 3
    assert manager.retry_delay == 1
    assert manager.gmail_client is None


@patch("dewey.core.crm.gmail.gmail_sync_manager.GmailClient")
def test_initialize_gmail_service(mock_gmail_client, temp_db_path):
    """Test Gmail service initialization."""
    # Setup mock
    mock_client = MagicMock()
    mock_gmail_client.return_value = mock_client
    mock_client.authenticate.return_value = MagicMock()

    # Initialize manager and service
    manager = GmailSyncManager(db_path=temp_db_path)
    result = manager.initialize_gmail_service()

    # Verify
    assert result is True
    assert manager.gmail_client == mock_client
    mock_client.authenticate.assert_called_once()


def test_initialize_database(temp_db_path):
    """Test database initialization."""
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()

    # Verify tables exist
    with duckdb.connect(str(temp_db_path)) as conn:
        tables = conn.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND 
            name IN ('emails', 'sync_status', 'sync_errors')
        """
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "emails" in table_names
        assert "sync_status" in table_names
        assert "sync_errors" in table_names


def test_check_consistency(temp_db_path, mock_gmail_service, sample_email_batch):
    """Test email consistency checking."""
    # Setup
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()
    manager.gmail_client = MagicMock()

    # Mock Gmail response
    mock_response = {"messages": sample_email_batch}
    manager.gmail_client.fetch_emails.return_value = mock_response

    # Run consistency check
    missing_local, missing_cloud = manager.check_consistency(
        days_back=7, check_sent=True
    )

    # Verify
    assert isinstance(missing_local, list)
    assert isinstance(missing_cloud, list)
    manager.gmail_client.fetch_emails.assert_called()


@patch("dewey.core.crm.gmail.gmail_sync_manager.GmailClient")
def test_sync_emails(mock_gmail_client, temp_db_path, sample_email_data):
    """Test email synchronization."""
    # Setup
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()

    # Mock Gmail client
    mock_client = MagicMock()
    mock_gmail_client.return_value = mock_client
    mock_client.authenticate.return_value = MagicMock()
    mock_client.get_message.return_value = sample_email_data

    # Run sync
    email_ids = ["msg1", "msg2"]
    result = manager.sync_emails(email_ids)

    # Verify
    assert result is True
    assert mock_client.get_message.call_count == len(email_ids)


def test_process_message(temp_db_path, sample_email_data):
    """Test message processing and storage."""
    # Setup
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()

    # Process message
    result = manager.process_message(sample_email_data)

    # Verify message was stored
    assert result is True
    with duckdb.connect(str(temp_db_path)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE gmail_id = ?", [sample_email_data["id"]]
        ).fetchone()[0]
        assert count == 1


def test_record_sync_error(temp_db_path):
    """Test error recording."""
    # Setup
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()

    # Record error
    error_msg = "Test error"
    email_id = "msg123"
    manager.record_sync_error(email_id, error_msg)

    # Verify error was recorded
    with duckdb.connect(str(temp_db_path)) as conn:
        result = conn.execute(
            "SELECT email_id, error_message FROM sync_errors WHERE email_id = ?",
            [email_id],
        ).fetchone()
        assert result[0] == email_id
        assert result[1] == error_msg


def test_retry_failed_syncs(temp_db_path, sample_email_data):
    """Test retrying failed synchronizations."""
    # Setup
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()
    manager.gmail_client = MagicMock()
    manager.gmail_client.get_message.return_value = sample_email_data

    # Add a failed sync
    manager.record_sync_error("msg123", "Initial failure")

    # Retry failed syncs
    result = manager.retry_failed_syncs()

    # Verify
    assert result is True
    with duckdb.connect(str(temp_db_path)) as conn:
        error_count = conn.execute(
            "SELECT COUNT(*) FROM sync_errors WHERE email_id = 'msg123'"
        ).fetchone()[0]
        assert error_count == 0


def test_update_sync_status(temp_db_path):
    """Test sync status updates."""
    # Setup
    manager = GmailSyncManager(db_path=temp_db_path)
    manager.initialize_database()

    # Update status
    sync_type = "incremental"
    status = "completed"
    manager.update_sync_status(sync_type, status)

    # Verify
    with duckdb.connect(str(temp_db_path)) as conn:
        result = conn.execute(
            "SELECT sync_type, status FROM sync_status ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        assert result[0] == sync_type
        assert result[1] == status
