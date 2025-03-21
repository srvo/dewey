"""Tests for database schema management.

This module tests the schema creation, migration, and versioning functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, call

import duckdb
import pytest

from src.dewey.core.db.schema import (
    initialize_schema,
    get_current_version,
    apply_migration,
    verify_schema_consistency
)

class TestSchemaManagement(unittest.TestCase):
    """Test schema management functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock database manager
        self.db_manager_patcher = patch('src.dewey.core.db.schema.db_manager')
        self.mock_db_manager = self.db_manager_patcher.start()
        
        # Mock connection
        self.mock_conn = MagicMock()
        self.mock_db_manager.get_connection.return_value.__enter__.return_value = self.mock_conn
        
        # Mock execute_query to return successful results
        self.mock_db_manager.execute_query.return_value = [(1,)]
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()
    
    def test_initialize_schema(self):
        """Test schema initialization."""
        # Call initialize schema
        initialize_schema()
        
        # Check that execute_query was called multiple times for different tables
        self.assertTrue(self.mock_db_manager.execute_query.call_count > 1)
        
        # Check that the schema_versions table was created
        calls = self.mock_db_manager.execute_query.call_args_list
        schema_version_call = None
        
        for call_args in calls:
            if 'CREATE TABLE IF NOT EXISTS schema_versions' in call_args[0][0]:
                schema_version_call = call_args
                break
                
        self.assertIsNotNone(schema_version_call, "schema_versions table was not created")
    
    def test_get_current_version_no_versions(self):
        """Test getting current version when no versions exist."""
        # Mock execute_query to return empty result
        self.mock_db_manager.execute_query.return_value = []
        
        # Get current version
        version = get_current_version()
        
        # Check result
        self.assertEqual(version, 0)
        
        # Check that execute_query was called with correct query
        self.mock_db_manager.execute_query.assert_called_with(
            "\n            SELECT MAX(version) FROM schema_versions\n            WHERE status = 'success'\n        ", local_only=False
        )
    
    def test_get_current_version_with_versions(self):
        """Test getting current version when versions exist."""
        # Mock execute_query to return a version
        self.mock_db_manager.execute_query.return_value = [(5,)]
        
        # Get current version
        version = get_current_version()
        
        # Check result
        self.assertEqual(version, 5)
    
    def test_apply_migration(self):
        """Test applying a migration."""
        # Apply migration
        apply_migration(1, "Test migration", "CREATE TABLE test (id INTEGER)")
        
        # Check that execute_query was called for transaction start, migration SQL, version update, and commit
        self.assertEqual(self.mock_db_manager.execute_query.call_count, 4)
        
        # Check the calls were made in the correct order
        calls = self.mock_db_manager.execute_query.call_args_list
        self.assertEqual(calls[0][0][0], "BEGIN TRANSACTION")
        self.assertEqual(calls[1][0][0], "CREATE TABLE test (id INTEGER)")
        self.assertIn("INSERT INTO schema_versions", calls[2][0][0])
        self.assertEqual(calls[3][0][0], "COMMIT")
    
    def test_verify_schema_consistency(self):
        """Test verifying schema consistency."""
        # Mock execute_query for local and MotherDuck schema versions
        with patch('src.dewey.core.db.schema.get_current_version') as mock_version:
            # Both databases have the same version
            mock_version.side_effect = [5, 5]
            
            # Mock the table schema comparison to return the same schemas
            table_schema = [("column1", "INTEGER"), ("column2", "VARCHAR")]
            self.mock_db_manager.execute_query.return_value = table_schema
            
            # Verify schema consistency
            result = verify_schema_consistency()
            
            # Check result - the function returns True directly, not a dict
            self.assertTrue(result)
            
            # Test with inconsistent versions
            mock_version.side_effect = [5, 3]
            
            # This will raise an exception internally and return False
            result = verify_schema_consistency()
            
            # Check result - should be False since versions don't match
            self.assertFalse(result)

if __name__ == '__main__':
    unittest.main() 