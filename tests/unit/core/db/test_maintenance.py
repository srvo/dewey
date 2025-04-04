r"""
Tests for DatabaseMaintenance class operations.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.dewey.core.db.operations import DatabaseMaintenance
from src.dewey.core.db.connection import DatabaseConnectionError

class TestDatabaseMaintenance(unittest.TestCase):
    """Test DatabaseMaintenance operations."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the database manager
        self.db_manager_patcher = patch("src.dewey.core.db.operations.db_manager")
        self.mock_db_manager = self.db_manager_patcher.start()

        # Mock logger
        self.logger_patcher = patch("src.dewey.core.db.operations.logger")
        self.mock_logger = self.logger_patcher.start()

        # Create test instance
        self.maintenance = DatabaseMaintenance(dry_run=False)

    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()
        self.logger_patcher.stop()

    def test_cleanup_tables(self):
        """Test table cleanup operation."""
        tables = ["table1", "table2"]

        # Test successful cleanup
        self.maintenance.cleanup_tables(tables)

        # Verify DELETE queries were executed
        self.assertEqual(self.mock_db_manager.execute_query.call_count, len(tables))
        self.mock_logger.info.assert_any_call("Cleaning table: table1")
        self.mock_logger.info.assert_any_call("Cleaned table: table1")

        # Test dry run
        self.maintenance.dry_run = True
        self.maintenance.cleanup_tables(tables)
        self.mock_logger.info.assert_any_call("[DRY RUN] Would clean tables: ['table1', 'table2']")

        # Test error handling
        self.mock_db_manager.execute_query.side_effect = Exception("Test error")
        with self.assertRaises(DatabaseConnectionError):
            self.maintenance.cleanup_tables(tables)

    def test_analyze_tables(self):
        """Test table analysis operation."""
        tables = ["table1", "table2"]

        # Mock query responses
        self.mock_db_manager.execute_query.side_effect = [
            [(100,)],  # row count for table1
            [(1024,)],  # size for table1
            [(200,)],   # row count for table2
            [(2048,)],  # size for table2
        ]

        results = self.maintenance.analyze_tables(tables)

        # Verify results
        self.assertEqual(results["table1"]["row_count"], 100)
        self.assertEqual(results["table1"]["size_bytes"], 1024)
        self.assertEqual(results["table2"]["row_count"], 200)
        self.assertEqual(results["table2"]["size_bytes"], 2048)

        # Verify logging
        self.mock_logger.info.assert_any_call("Analyzing table: table1")
        self.mock_logger.info.assert_any_call("Analysis complete for table1: {'row_count': 100, 'size_bytes': 1024}")

    def test_drop_tables(self):
        """Test table dropping operation."""
        tables = ["table1", "table2"]

        self.maintenance.drop_tables(tables)

        # Verify DROP queries were executed
        self.assertEqual(self.mock_db_manager.execute_query.call_count, len(tables))
        self.mock_logger.info.assert_any_call("Dropping table: table1")
        self.mock_logger.info.assert_any_call("Dropped table: table1")

        # Test dry run
        self.maintenance.dry_run = True
        self.maintenance.drop_tables(tables)
        self.mock_logger.info.assert_any_call("[DRY RUN] Would drop tables: ['table1', 'table2']")

    def test_force_cleanup(self):
        """Test force cleanup operation."""
        # Mock table list
        self.mock_db_manager.execute_query.side_effect = [
            [("table1",), ("table2",)],  # list tables
            None,  # drop table1
            None,  # drop table2
            None,  # schema cleanup
        ]

        self.maintenance.force_cleanup()

        # Verify operations
        self.mock_logger.info.assert_any_call("Starting force cleanup...")
        self.mock_logger.info.assert_any_call("Dropping table: table1")
        self.mock_logger.info.assert_any_call("Cleaning up other database objects")
        self.mock_logger.info.assert_any_call("Force cleanup completed")

    def test_upload_database(self):
        """Test database upload operation."""
        db_name = "test_db"
        destination = "remote_location"

        # Add upload method to mock
        self.mock_db_manager.upload = MagicMock()

        self.maintenance.upload_database(db_name, destination)

        # Verify operations
        self.mock_logger.info.assert_any_call(
            f"Starting upload of {db_name} to {destination}"
        )
        self.mock_logger.info.assert_any_call(
            f"Successfully uploaded {db_name} to {destination}"
        )
        self.mock_db_manager.upload.assert_called_once_with(db_name, destination)

        # Test error handling
        self.mock_db_manager.upload.side_effect = Exception("Upload failed")
        with self.assertRaises(DatabaseConnectionError):
            self.maintenance.upload_database(db_name, destination)

    def test_handle_database_connection_error(self):
        """Test handling of DatabaseConnectionError."""
        self.mock_db_manager.execute_query.side_effect = DatabaseConnectionError(
            "Failed to connect to the database"
        )
        with self.assertRaises(DatabaseConnectionError):
            self.maintenance.cleanup_tables(["table1"])

if __name__ == "__main__":
    unittest.main()