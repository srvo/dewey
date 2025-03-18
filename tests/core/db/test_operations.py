"""Tests for database operations."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from dewey.core.db.operations import (
    transaction, record_change, insert_record, update_record,
    delete_record, get_record, query_records, bulk_insert,
    execute_custom_query
)
from dewey.core.db.errors import DatabaseError

@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    with patch('dewey.core.db.operations.db_manager') as mock_manager:
        mock_manager.is_online.return_value = True
        yield mock_manager

def test_transaction_context():
    """Test transaction context manager."""
    with patch('dewey.core.db.operations.db_manager') as mock_manager:
        # Test successful transaction
        with transaction():
            mock_manager.execute_query.assert_called_with(
                "BEGIN TRANSACTION", for_write=True, local_only=False
            )
        mock_manager.execute_query.assert_called_with(
            "COMMIT", for_write=True, local_only=False
        )
        
        # Test failed transaction
        mock_manager.execute_query.reset_mock()
        with pytest.raises(ValueError):
            with transaction():
                raise ValueError("Test error")
        mock_manager.execute_query.assert_called_with(
            "ROLLBACK", for_write=True, local_only=False
        )

def test_record_change(mock_db_manager):
    """Test recording changes."""
    record_change("test_table", "INSERT", "123", {"name": "test"}, "user1")
    
    # Verify change was recorded
    mock_db_manager.execute_query.assert_called_with(
        """
                INSERT INTO change_log (
                    table_name, operation, record_id, 
                    changed_at, user_id, details
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
        ["test_table", "INSERT", "123", "user1", {"name": "test"}],
        for_write=True,
        local_only=True
    )

def test_insert_record(mock_db_manager):
    """Test inserting a record."""
    data = {"id": "123", "name": "test"}
    record_id = insert_record("test_table", data)
    
    assert record_id == "123"
    mock_db_manager.execute_query.assert_called_with(
        "INSERT INTO test_table (id, name) VALUES (?, ?)",
        ["123", "test"],
        for_write=True,
        local_only=True
    )

def test_update_record(mock_db_manager):
    """Test updating a record."""
    mock_db_manager.execute_query.return_value = [(1,)]
    data = {"name": "updated"}
    update_record("test_table", "123", data)
    
    mock_db_manager.execute_query.assert_called_with(
        "UPDATE test_table SET name = ? WHERE id = ?",
        ["updated", "123"],
        for_write=True,
        local_only=True
    )

def test_delete_record(mock_db_manager):
    """Test deleting a record."""
    mock_db_manager.execute_query.return_value = [("123", "test")]
    delete_record("test_table", "123")
    
    # Verify record was deleted
    mock_db_manager.execute_query.assert_called_with(
        "DELETE FROM test_table WHERE id = ?",
        ["123"],
        for_write=True,
        local_only=True
    )

def test_get_record(mock_db_manager):
    """Test getting a record."""
    mock_db_manager.execute_query.side_effect = [
        [("123", "test")],  # Record data
        [("id", "VARCHAR"), ("name", "VARCHAR")]  # Schema data
    ]
    
    record = get_record("test_table", "123")
    assert record == {"id": "123", "name": "test"}

def test_query_records(mock_db_manager):
    """Test querying records."""
    mock_db_manager.execute_query.side_effect = [
        [("123", "test1"), ("456", "test2")],  # Query results
        [("id", "VARCHAR"), ("name", "VARCHAR")]  # Schema data
    ]
    
    conditions = {"name": "test"}
    records = query_records("test_table", conditions, order_by="name", limit=10)
    
    assert len(records) == 2
    assert records[0]["name"] == "test1"
    assert records[1]["name"] == "test2"

def test_bulk_insert(mock_db_manager):
    """Test bulk inserting records."""
    records = [
        {"id": "123", "name": "test1"},
        {"id": "456", "name": "test2"}
    ]
    
    record_ids = bulk_insert("test_table", records)
    assert record_ids == ["123", "456"]
    
    # Verify both records were inserted
    assert mock_db_manager.execute_query.call_count >= 2

def test_execute_custom_query(mock_db_manager):
    """Test executing custom queries."""
    mock_db_manager.execute_query.return_value = [(1, "test")]
    
    # Test read query
    result = execute_custom_query("SELECT * FROM test")
    assert result == [(1, "test")]
    mock_db_manager.execute_query.assert_called_with(
        "SELECT * FROM test", None, False, False
    )
    
    # Test write query
    result = execute_custom_query("UPDATE test SET name = 'test'", for_write=True)
    assert result == [(1, "test")]
    mock_db_manager.execute_query.assert_called_with(
        "UPDATE test SET name = 'test'", None, True, True
    ) 