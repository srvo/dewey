"""
Tests for database monitoring and health check functionality.

This module tests the database monitoring and health check functions.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.dewey.core.db.monitor import (
    check_connection,
    check_sync_health,
    check_table_health,
    monitor_database,
    run_health_check,
)


class TestDatabaseMonitor(unittest.TestCase):
    """Test the database monitoring functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock database manager
        self.db_manager_patcher = patch("src.dewey.core.db.monitor.db_manager")
        self.mock_db_manager = self.db_manager_patcher.start()

        # Mock connection
        self.mock_conn = MagicMock()
        self.mock_db_manager.get_connection.return_value.__enter__.return_value = (
            self.mock_conn
        )

        # Mock execute_query
        self.mock_db_manager.execute_query.return_value = [(1,)]

        # Mock get_db_config
        self.config_patcher = patch("src.dewey.core.db.monitor.get_db_config")
        self.mock_config = self.config_patcher.start()
        self.mock_config.return_value = {
            "sync_interval": 3600,
            "local_db_path": "/path/to/db.duckdb",
        }

        # Mock os.path.getsize
        self.getsize_patcher = patch("os.path.getsize")
        self.mock_getsize = self.getsize_patcher.start()
        self.mock_getsize.return_value = 1024 * 1024  # 1MB

    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()
        self.config_patcher.stop()
        self.getsize_patcher.stop()

    def test_check_connection(self):
        """Test checking database connection health."""
        # Test successful connection
        result = check_connection()
        self.assertTrue(result)

        # Check that execute_query was called with correct query
        self.mock_db_manager.execute_query.assert_called_once_with(
            "SELECT 1", local_only=False,
        )

        # Test failed connection
        self.mock_db_manager.execute_query.side_effect = Exception("Connection failed")
        result = check_connection()
        self.assertFalse(result)

    def test_check_table_health(self):
        """Test checking table health."""
        # Create a datetime object for testing
        test_date = datetime(2023, 1, 1, 12, 0, 0)

        # Mock query results for the two queries in check_table_health
        self.mock_db_manager.execute_query.side_effect = [
            # First query returns statistics
            [(100, 0, test_date, test_date)],
            # Second query returns duplicate IDs (empty result = no duplicates)
            [],
        ]

        # Check table health
        result = check_table_health("test_table")

        # Check results
        self.assertTrue(result["healthy"])
        self.assertEqual(result["row_count"], 100)
        self.assertEqual(result["null_ids"], 0)
        self.assertIn("oldest_record", result)
        self.assertIn("newest_record", result)
        self.assertFalse(result["has_duplicates"])
        self.assertEqual(result["duplicate_count"], 0)
        self.assertEqual(result["issues"], [])

    def test_check_sync_health(self):
        """Test checking sync health."""
        # Reset the side_effect from previous tests
        self.mock_db_manager.execute_query.side_effect = None

        # Mock get_last_sync_time
        with patch("src.dewey.core.db.monitor.get_last_sync_time") as mock_sync:
            # Mock recent sync (less than sync_interval)
            now = datetime.now()
            # Set a recent timestamp (30 minutes ago) to avoid is_overdue=True
            mock_sync.return_value = now - timedelta(minutes=30)

            # Mock conflict and failed sync queries to return 0 conflicts and 0 failures
            self.mock_db_manager.execute_query.side_effect = [
                [(0,)],  # No unresolved conflicts
                [(0,)],  # No failed syncs
            ]

            # Check sync health
            result = check_sync_health()

            # Check results - should be healthy since all conditions are good
            self.assertTrue(
                result["healthy"], f"Expected healthy sync but got {result}",
            )
            self.assertIn("last_sync", result)
            self.assertEqual(result["unresolved_conflicts"], 0)
            self.assertEqual(result["recent_failures"], 0)
            self.assertFalse(result["is_overdue"])

    def test_run_health_check(self):
        """Test running full health check."""
        # Mock individual health check functions
        with patch("src.dewey.core.db.monitor.check_connection") as mock_conn:
            mock_conn.side_effect = [True, True]  # local and motherduck connections

            with patch("src.dewey.core.db.monitor.check_sync_health") as mock_sync:
                mock_sync.return_value = {"healthy": True}

                with patch(
                    "src.dewey.core.db.monitor.check_schema_consistency",
                ) as mock_schema:
                    mock_schema.return_value = {"consistent": True}

                    with patch(
                        "src.dewey.core.db.monitor.check_database_size",
                    ) as mock_size:
                        mock_size.return_value = {"file_size_bytes": 1024 * 1024}

                        with patch(
                            "src.dewey.core.db.monitor.check_table_health",
                        ) as mock_table:
                            mock_table.return_value = {"healthy": True}

                            # Mock TABLES list
                            with patch(
                                "src.dewey.core.db.monitor.TABLES", ["test_table"],
                            ):
                                # Run health check
                                result = run_health_check(include_performance=False)

                                # Check results
                                self.assertTrue(result["healthy"])
                                self.assertTrue(result["connection"]["local"])
                                self.assertTrue(result["connection"]["motherduck"])
                                self.assertTrue(result["sync"]["healthy"])
                                self.assertTrue(result["schema"]["consistent"])
                                self.assertTrue(
                                    result["tables"]["test_table"]["healthy"],
                                )
                                self.assertIn("timestamp", result)
                                self.assertNotIn("performance", result)


class TestMonitorFunctions(unittest.TestCase):
    """Test the database monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock run_health_check
        self.health_check_patcher = patch("src.dewey.core.db.monitor.run_health_check")
        self.mock_health_check = self.health_check_patcher.start()
        self.mock_health_check.return_value = {"healthy": True}

        # Mock time.sleep to avoid waiting in tests
        self.sleep_patcher = patch("time.sleep")
        self.mock_sleep = self.sleep_patcher.start()

    def tearDown(self):
        """Tear down test fixtures."""
        self.health_check_patcher.stop()
        self.sleep_patcher.stop()

    def test_monitor_database(self):
        """Test database monitoring function."""
        # Set the _monitoring_active flag to False to force immediate exit
        with patch("src.dewey.core.db.monitor._monitoring_active", False):
            # Now we can call the actual function with run_once=True
            # to make it exit after one iteration
            monitor_database(interval=1, run_once=True)

            # Verify health check was called
            self.mock_health_check.assert_called_once()

            # No need to check sleep since we're exiting immediately with _monitoring_active=False


if __name__ == "__main__":
    unittest.main()
