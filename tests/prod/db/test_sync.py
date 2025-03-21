"""Tests for database synchronization.

This module tests synchronization between local and MotherDuck databases.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

import duckdb
import pytest

from src.dewey.core.db.sync import (
    record_sync_status,
    get_last_sync_time,
    get_changes_since,
    detect_conflicts,
    resolve_conflicts,
    apply_changes,
    sync_table,
    sync_all_tables,
    SyncError
)

class TestSyncFunctions(unittest.TestCase):
    """Test synchronization functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock database manager
        self.db_manager_patcher = patch('src.dewey.core.db.sync.db_manager')
        self.mock_db_manager = self.db_manager_patcher.start()
        
        # Mock connection
        self.mock_conn = MagicMock()
        self.mock_db_manager.get_connection.return_value.__enter__.return_value = self.mock_conn
        
        # Mock execute_query to return successful results
        self.mock_db_manager.execute_query.return_value = [('1',)]
        
        # Set a reference to the mock_db_manager in utils module
        # to handle record_sync_status
        from src.dewey.core.db.utils import set_db_manager
        set_db_manager(self.mock_db_manager)
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Clear the db_manager reference in utils
        from src.dewey.core.db.utils import set_db_manager
        set_db_manager(None)
        
        self.db_manager_patcher.stop()
    
    def test_record_sync_status(self):
        """Test recording sync status."""
        # Mock utils.db_manager since that's what actually gets used
        with patch('src.dewey.core.db.utils.db_manager') as mock_utils_db_manager:
            # Record sync status
            record_sync_status("success", "Sync completed", {"table": "test_table"})
            
            # Check that execute_query was called with correct arguments
            mock_utils_db_manager.execute_query.assert_called_once()
            
            # Check that parameters for the query include the status and message
            call_args = mock_utils_db_manager.execute_query.call_args[0]
            self.assertIn("INSERT INTO sync_status", call_args[0])
            self.assertEqual(call_args[1][0], "success")
            self.assertEqual(call_args[1][1], "Sync completed")
    
    def test_get_last_sync_time(self):
        """Test getting last sync time."""
        # Mock execute_query to return a timestamp
        now = datetime.now()
        self.mock_db_manager.execute_query.return_value = [(now,)]
        
        # Get last sync time
        result = get_last_sync_time()
        
        # Check that execute_query was called with correct arguments
        self.mock_db_manager.execute_query.assert_called_once()
        
        # Check that the query is selecting from sync_status
        call_args = self.mock_db_manager.execute_query.call_args[0]
        self.assertIn("SELECT created_at FROM sync_status", call_args[0])
        
        # Check result
        self.assertEqual(result, now)
    
    def test_get_changes_since(self):
        """Test getting changes since a timestamp."""
        # Mock execute_query to return changes
        test_changes = [
            {"record_id": "1", "operation": "UPDATE", "table_name": "test_table"}
        ]
        self.mock_db_manager.execute_query.return_value = [(
            "1", "UPDATE", "test_table", "2023-01-01T12:00:00", "user1", '{"field":"value"}'
        )]
        
        # Mock get_column_names
        with patch('src.dewey.core.db.sync.get_column_names') as mock_cols:
            mock_cols.return_value = [
                "record_id", "operation", "table_name", "changed_at", "user_id", "details"
            ]
            
            # Get changes
            since = datetime(2023, 1, 1)
            changes = get_changes_since("test_table", since)
            
            # Check that execute_query was called with correct arguments
            self.mock_db_manager.execute_query.assert_called_once()
            
            # Check that the query includes the table name and timestamp
            call_args = self.mock_db_manager.execute_query.call_args[0]
            self.assertIn("SELECT", call_args[0])
            self.assertIn("FROM change_log", call_args[0])
            self.assertIn("WHERE table_name = ?", call_args[0])
            self.assertIn("AND changed_at >= ?", call_args[0])
            
            # Check that the parameters include the table name and timestamp
            self.assertEqual(call_args[1][0], "test_table")
            
            # Check results
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]["record_id"], "1")
            self.assertEqual(changes[0]["operation"], "UPDATE")
    
    def test_detect_conflicts(self):
        """Test detecting conflicts."""
        # Create sample changes
        local_changes = [
            {"record_id": "1", "operation": "UPDATE", "changed_at": "2023-01-01T12:00:00"},
            {"record_id": "2", "operation": "INSERT", "changed_at": "2023-01-01T12:30:00"}
        ]
        
        remote_changes = [
            {"record_id": "1", "operation": "UPDATE", "changed_at": "2023-01-01T12:15:00"},
            {"record_id": "3", "operation": "DELETE", "changed_at": "2023-01-01T12:45:00"}
        ]
        
        # Detect conflicts
        conflicts = detect_conflicts("test_table", local_changes, remote_changes)
        
        # Check conflicts - should find one conflict (record_id=1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["record_id"], "1")
        self.assertEqual(conflicts[0]["table_name"], "test_table")
    
    def test_apply_changes(self):
        """Test applying changes."""
        # Create sample changes
        changes = [
            {"record_id": "1", "operation": "UPDATE", "details": {"name": "Updated"}, "table_name": "test_table"},
            {"record_id": "2", "operation": "INSERT", "details": {"name": "New"}, "table_name": "test_table"}
        ]
        
        # Apply changes
        apply_changes("test_table", changes)
        
        # Check that execute_query was called multiple times (once per change)
        self.assertEqual(self.mock_db_manager.execute_query.call_count, 2)
    
    def test_sync_table(self):
        """Test syncing a table."""
        # Mock get_last_sync_time
        with patch('src.dewey.core.db.sync.get_last_sync_time') as mock_last_sync:
            last_sync = datetime(2023, 1, 1)
            mock_last_sync.return_value = last_sync
            
            # Mock get_changes_since
            with patch('src.dewey.core.db.sync.get_changes_since') as mock_changes:
                # No changes in either database
                mock_changes.side_effect = [[], []]
                
                # Sync table
                changes_applied, conflicts = sync_table("test_table", last_sync)
                
                # Check results
                self.assertEqual(changes_applied, 0)
                self.assertEqual(conflicts, 0)
                
                # Test with local changes
                mock_changes.side_effect = [
                    [{"record_id": "1", "operation": "UPDATE"}],
                    []
                ]
                
                # Mock apply_changes
                with patch('src.dewey.core.db.sync.apply_changes') as mock_apply:
                    # Sync table
                    changes_applied, conflicts = sync_table("test_table", last_sync)
                    
                    # Check results
                    self.assertEqual(changes_applied, 1)
                    self.assertEqual(conflicts, 0)
                    
                    # Check that apply_changes was called
                    mock_apply.assert_called_once()
    
    def test_sync_all_tables(self):
        """Test syncing all tables."""
        # Mock TABLES constant
        with patch('src.dewey.core.db.sync.TABLES', ["table1", "table2"]):
            # Mock sync_table
            with patch('src.dewey.core.db.sync.sync_table') as mock_sync:
                mock_sync.side_effect = [(2, 0), (3, 1)]
                
                # Sync all tables
                result = sync_all_tables()
                
                # Check results
                self.assertEqual(len(result), 2)
                self.assertEqual(result["table1"], (2, 0))
                self.assertEqual(result["table2"], (3, 1))
                
                # Check that sync_table was called twice
                self.assertEqual(mock_sync.call_count, 2)

if __name__ == '__main__':
    unittest.main() 