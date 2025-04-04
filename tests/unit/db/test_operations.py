"""
Tests for database CRUD operations and transactions.

This module tests the database operations functionality.
"""

import unittest
from unittest.mock import patch

from src.dewey.core.db.operations import (
    bulk_insert,
    delete_record,
    execute_custom_query,
    get_column_names,
    get_record,
    insert_record,
    query_records,
    record_change,
    update_record,
)


class TestCRUDOperations(unittest.TestCase):
    """Test CRUD operations."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock database manager
        self.db_manager_patcher = patch("src.dewey.core.db.operations.db_manager")
        self.mock_db_manager = self.db_manager_patcher.start()

        # Mock record_change function
        self.record_change_patcher = patch("src.dewey.core.db.operations.record_change")
        self.mock_record_change = self.record_change_patcher.start()

        # Mock the database functionality
        def mock_execute_query(query, params=None, for_write=False):
            if "INSERT" in query and "RETURNING" in query:
                return [("1",)]
            if "UPDATE" in query:
                return [("update",)]
            if "DELETE" in query:
                return [("delete",)]
            if "DESCRIBE" in query:
                return [("id", "INTEGER", "NO"), ("name", "VARCHAR", "YES")]
            # Read operations
            return [("1", "Test", 42)]

        self.mock_db_manager.execute_query.side_effect = mock_execute_query

    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()
        self.record_change_patcher.stop()

    def test_get_column_names(self):
        """Test getting column names for a table."""
        # Override the general mock for this specific test
        self.mock_db_manager.execute_query.side_effect = None
        self.mock_db_manager.execute_query.return_value = [
            ("id", "INTEGER", "NO", None, None, "PK"),
            ("name", "VARCHAR", "YES", None, None, ""),
            ("value", "INTEGER", "YES", None, None, ""),
        ]

        # Get column names
        column_names = get_column_names("test_table")

        # Check that execute_query was called with the correct query
        self.mock_db_manager.execute_query.assert_called_once_with(
            "DESCRIBE test_table",
        )

        # Check result
        self.assertEqual(column_names, ["id", "name", "value"])

        # Test error handling
        self.mock_db_manager.execute_query.reset_mock()
        self.mock_db_manager.execute_query.side_effect = Exception("Test error")

        # This should return an empty list instead of raising an exception
        result = get_column_names("test_table")
        self.assertEqual(result, [])

    def test_insert_record(self):
        """Test inserting a record."""
        data = {"name": "Test", "value": 42}

        # Call the function
        record_id = insert_record("test_table", data)

        # Check that INSERT query was executed
        insert_calls = [
            call
            for call in self.mock_db_manager.execute_query.call_args_list
            if "INSERT INTO test_table" in call[0][0]
        ]
        self.assertTrue(len(insert_calls) > 0, "INSERT query not called")

        # Check that record_change was called
        self.assertTrue(self.mock_record_change.called, "record_change not called")

    def test_update_record(self):
        """Test updating a record."""
        data = {"name": "Updated"}

        # Call the function
        update_record("test_table", "1", data)

        # Check that UPDATE query was executed
        update_calls = [
            call
            for call in self.mock_db_manager.execute_query.call_args_list
            if "UPDATE test_table" in call[0][0]
        ]
        self.assertTrue(len(update_calls) > 0, "UPDATE query not called")

        # Check that record_change was called
        self.assertTrue(self.mock_record_change.called, "record_change not called")

    def test_delete_record(self):
        """Test deleting a record."""
        # Call the function
        delete_record("test_table", "1")

        # Check that DELETE query was executed
        delete_calls = [
            call
            for call in self.mock_db_manager.execute_query.call_args_list
            if "DELETE FROM test_table" in call[0][0]
        ]
        self.assertTrue(len(delete_calls) > 0, "DELETE query not called")

        # Check that record_change was called
        self.assertTrue(self.mock_record_change.called, "record_change not called")

    def test_get_record(self):
        """Test getting a record."""
        # Override the general mock for this specific test
        self.mock_db_manager.execute_query.side_effect = None
        self.mock_db_manager.execute_query.return_value = [(1, "Test", 42)]

        # Mock column names
        with patch("src.dewey.core.db.operations.get_column_names") as mock_cols:
            mock_cols.return_value = ["id", "name", "value"]

            # Get record
            record = get_record("test_table", "1")

            # Make sure the SELECT query was called
            select_calls = [
                call
                for call in self.mock_db_manager.execute_query.call_args_list
                if "SELECT * FROM test_table" in call[0][0]
            ]
            self.assertTrue(len(select_calls) > 0, "SELECT query not called")

            # Check result
            self.assertEqual(record["id"], 1)
            self.assertEqual(record["name"], "Test")
            self.assertEqual(record["value"], 42)

    def test_query_records(self):
        """Test querying records."""
        # Override the general mock for this specific test
        self.mock_db_manager.execute_query.side_effect = None
        self.mock_db_manager.execute_query.return_value = [
            (1, "Test1", 42),
            (2, "Test2", 43),
        ]

        # Mock column names
        with patch("src.dewey.core.db.operations.get_column_names") as mock_cols:
            mock_cols.return_value = ["id", "name", "value"]

            # Query records
            records = query_records(
                "test_table", {"value": 42}, order_by="id", limit=10,
            )

            # Make sure the SELECT query was called with proper conditions
            select_calls = [
                call
                for call in self.mock_db_manager.execute_query.call_args_list
                if "SELECT * FROM test_table" in call[0][0] and "WHERE" in call[0][0]
            ]
            self.assertTrue(len(select_calls) > 0, "SELECT query with WHERE not called")

            # Check results
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["id"], 1)
            self.assertEqual(records[0]["name"], "Test1")
            self.assertEqual(records[1]["id"], 2)

    def test_bulk_insert(self):
        """Test bulk inserting records."""
        # Create test data
        records = [{"name": "Test1", "value": 42}, {"name": "Test2", "value": 43}]

        # Call the function
        record_ids = bulk_insert("test_table", records)

        # Check that INSERT queries were executed for each record
        insert_calls = [
            call
            for call in self.mock_db_manager.execute_query.call_args_list
            if "INSERT INTO test_table" in call[0][0]
        ]
        self.assertTrue(len(insert_calls) > 0, "INSERT queries not called")

        # Check that record_change was called for each record
        self.assertTrue(
            self.mock_record_change.call_count > 0, "record_change not called",
        )

    def test_record_change(self):
        """Test recording a change."""
        record_change("test_table", "INSERT", "1", {"name": "Test"})

        # Check that execute_query was called with correct arguments
        self.mock_db_manager.execute_query.assert_called_once()

        # Check that parameters for the query include the table name and operation
        call_args = self.mock_db_manager.execute_query.call_args
        self.assertIn("INSERT INTO change_log", call_args[0][0])

    def test_execute_custom_query(self):
        """Test executing a custom query."""
        # Override the general mock for this specific test
        self.mock_db_manager.execute_query.side_effect = None
        self.mock_db_manager.execute_query.return_value = [(1, "Test")]

        # Execute query
        results = execute_custom_query("SELECT * FROM test_table WHERE id = ?", [1])

        # Check that execute_query was called with correct arguments
        query_calls = self.mock_db_manager.execute_query.call_args_list
        self.assertTrue(len(query_calls) > 0, "Query not executed")

        # Find the call with our specific query
        query_call = next(
            (
                call
                for call in query_calls
                if "SELECT * FROM test_table WHERE id = ?" in call[0][0]
            ),
            None,
        )
        self.assertIsNotNone(query_call, "Custom query not found in calls")

        # Check result
        self.assertEqual(results, [(1, "Test")])


if __name__ == "__main__":
    unittest.main()
