"""Tests for database synchronization."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from dewey.core.db.sync import (
    SyncManager,
    record_sync_status,
    get_last_sync_time,
    get_changes_since,
    detect_conflicts,
    resolve_conflicts,
    apply_changes,
    sync_table,
    sync_all_tables,
)
from dewey.core.db.errors import SyncError


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    with patch("dewey.core.db.sync.db_manager") as mock_manager:
        mock_manager.is_online.return_value = True
        yield mock_manager


@pytest.fixture
def sync_manager():
    """Create a test sync manager."""
    return SyncManager()


def test_sync_manager_queue_offline_change(sync_manager):
    """Test queuing offline changes."""
    change = {
        "table_name": "test",
        "operation": "INSERT",
        "record_id": "123",
        "details": {"name": "test"},
    }

    sync_manager.queue_offline_change(change)
    assert len(sync_manager.offline_changes) == 1
    assert sync_manager.offline_changes[0] == change


def test_sync_manager_sync_offline_changes(sync_manager, mock_db_manager):
    """Test syncing offline changes."""
    changes = [
        {
            "table_name": "test",
            "operation": "INSERT",
            "record_id": "123",
            "details": {"name": "test1"},
        },
        {
            "table_name": "test",
            "operation": "UPDATE",
            "record_id": "456",
            "details": {"name": "test2"},
        },
    ]

    for change in changes:
        sync_manager.queue_offline_change(change)

    synced = sync_manager.sync_offline_changes()
    assert synced == 2
    assert len(sync_manager.offline_changes) == 0


def test_record_sync_status(mock_db_manager):
    """Test recording sync status."""
    record_sync_status("success", "Test sync", {"details": "test"})

    mock_db_manager.execute_query.assert_called_with(
        """
            INSERT INTO sync_status (status, message, details)
            VALUES (?, ?, ?)
        """,
        ["success", "Test sync", {"details": "test"}],
        for_write=True,
        local_only=True,
    )


def test_get_last_sync_time(mock_db_manager):
    """Test getting last sync time."""
    now = datetime.now()
    mock_db_manager.execute_query.return_value = [(now,)]

    last_sync = get_last_sync_time()
    assert last_sync == now


def test_get_changes_since(mock_db_manager):
    """Test getting changes since timestamp."""
    now = datetime.now()
    mock_db_manager.execute_query.return_value = [
        (1, "test", "INSERT", "123", now, "user1", {"name": "test"})
    ]

    changes = get_changes_since("test", now - timedelta(hours=1))
    assert len(changes) == 1
    assert changes[0]["table_name"] == "test"
    assert changes[0]["operation"] == "INSERT"


def test_detect_conflicts():
    """Test conflict detection."""
    local_changes = [
        {"record_id": "123", "operation": "UPDATE", "details": {"name": "local"}}
    ]
    remote_changes = [
        {"record_id": "123", "operation": "UPDATE", "details": {"name": "remote"}}
    ]

    conflicts = detect_conflicts("test", local_changes, remote_changes)
    assert len(conflicts) == 1
    assert conflicts[0]["record_id"] == "123"
    assert conflicts[0]["conflict_type"] == "data_mismatch"


def test_resolve_conflicts(mock_db_manager):
    """Test conflict resolution."""
    conflicts = [
        {
            "table_name": "test",
            "record_id": "123",
            "operation": "conflict",
            "error_message": "Test conflict",
            "details": {"type": "data_mismatch"},
        }
    ]

    resolve_conflicts(conflicts)
    mock_db_manager.execute_query.assert_called_with(
        """
                INSERT INTO sync_conflicts (
                    table_name, record_id, operation, error_message,
                    sync_time, resolved, resolution_details
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, FALSE, ?)
            """,
        ["test", "123", "conflict", "Test conflict", {"type": "data_mismatch"}],
        for_write=True,
        local_only=True,
    )


def test_apply_changes(mock_db_manager):
    """Test applying changes."""
    changes = [
        {"operation": "INSERT", "record_id": "123", "details": {"name": "test"}},
        {"operation": "UPDATE", "record_id": "456", "details": {"name": "updated"}},
    ]

    apply_changes("test", changes)
    assert mock_db_manager.execute_query.call_count == 2


def test_sync_table(mock_db_manager):
    """Test table synchronization."""
    now = datetime.now()
    mock_db_manager.execute_query.return_value = []

    changes, conflicts = sync_table("test", now - timedelta(hours=1))
    assert changes == 0
    assert conflicts == 0


def test_sync_all_tables(mock_db_manager):
    """Test syncing all tables."""
    with patch("dewey.core.db.sync.TABLES", ["test1", "test2"]):
        mock_db_manager.execute_query.return_value = []

        results = sync_all_tables(max_age=timedelta(days=1))
        assert len(results) == 2
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results.values())


def test_sync_error_handling(mock_db_manager):
    """Test sync error handling."""
    mock_db_manager.execute_query.side_effect = Exception("Sync failed")

    with pytest.raises(SyncError):
        sync_table("test", datetime.now())
