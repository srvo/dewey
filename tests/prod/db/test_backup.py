"""
Tests for database backup and restore functionality.

This module tests the database backup and restore functions.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.dewey.core.db.backup import (
    BackupError,
    cleanup_old_backups,
    create_backup,
    export_table,
    import_table,
    list_backups,
    restore_backup,
    verify_backup,
)


class TestBackupFunctions(unittest.TestCase):
    """Test backup and restore functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for backups
        self.temp_dir = tempfile.mkdtemp()

        # Mock database manager
        self.db_manager_patcher = patch("src.dewey.core.db.backup.db_manager")
        self.mock_db_manager = self.db_manager_patcher.start()

        # Mock os functions
        self.path_exists_patcher = patch("os.path.exists")
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True

        # Mock BACKUP_DIR and LOCAL_DB_PATH
        self.backup_dir_patcher = patch(
            "src.dewey.core.db.backup.BACKUP_DIR", self.temp_dir,
        )
        self.mock_backup_dir = self.backup_dir_patcher.start()

        self.local_db_path_patcher = patch(
            "src.dewey.core.db.backup.LOCAL_DB_PATH",
            os.path.join(self.temp_dir, "dewey.duckdb"),
        )
        self.mock_local_db_path = self.local_db_path_patcher.start()

        # Create mock file for shutil.copy2
        open(os.path.join(self.temp_dir, "dewey.duckdb"), "w").close()

    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()
        self.path_exists_patcher.stop()
        self.backup_dir_patcher.stop()
        self.local_db_path_patcher.stop()

        # Clean up the temporary directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_create_backup(self):
        """Test creating a backup."""
        # Mock shutil.copy2
        with patch("shutil.copy2") as mock_copy:
            # Mock datetime
            with patch("src.dewey.core.db.backup.datetime") as mock_datetime:
                mock_now = datetime(2023, 1, 15, 12, 30, 45)
                mock_datetime.now.return_value = mock_now

                # Create backup
                backup_path = create_backup()

                # Check backup path
                expected_path = os.path.join(
                    self.temp_dir, "dewey_backup_20230115_123045.duckdb",
                )
                self.assertEqual(backup_path, expected_path)

                # Check that shutil.copy2 was called correctly
                mock_copy.assert_called_once_with(
                    os.path.join(self.temp_dir, "dewey.duckdb"), expected_path,
                )

    def test_create_backup_failure(self):
        """Test failure in creating a backup."""
        # Mock shutil.copy2 to raise an exception
        with patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = Exception("Copy failed")

            # Check that BackupError is raised
            with self.assertRaises(BackupError):
                create_backup()

    def test_restore_backup(self):
        """Test restoring from a backup."""
        # Create a mock backup file
        backup_path = os.path.join(self.temp_dir, "backup_test.duckdb")

        # Mock create_backup and shutil.copy2
        with patch("src.dewey.core.db.backup.create_backup") as mock_create:
            mock_create.return_value = os.path.join(
                self.temp_dir, "current_backup.duckdb",
            )

            with patch("shutil.copy2") as mock_copy:
                # Restore from backup
                restore_backup(backup_path)

                # Check that create_backup was called
                mock_create.assert_called_once()

                # Check that copy2 was called to restore the backup
                mock_copy.assert_called_with(
                    backup_path, os.path.join(self.temp_dir, "dewey.duckdb"),
                )

    def test_restore_backup_file_not_found(self):
        """Test error when backup file is not found."""
        # Mock os.path.exists to return False
        self.mock_path_exists.return_value = False

        # Create a mock backup path
        backup_path = os.path.join(self.temp_dir, "nonexistent.duckdb")

        # Check that BackupError is raised
        with self.assertRaises(BackupError):
            restore_backup(backup_path)

    def test_list_backups(self):
        """Test listing backups."""
        # Mock os.listdir
        with patch("os.listdir") as mock_listdir:
            mock_listdir.return_value = [
                "dewey_backup_20230101_120000.duckdb",
                "dewey_backup_20230102_120000.duckdb",
                "not_a_backup.txt",
            ]

            # Mock os.path.getsize
            with patch("os.path.getsize") as mock_getsize:
                # Return file sizes
                mock_getsize.side_effect = [1024 * 1024, 2 * 1024 * 1024]

                # List backups
                backups = list_backups()

                # Check backups
                self.assertEqual(len(backups), 2)

                # Check backup details
                self.assertIn("path", backups[0])
                self.assertIn("size", backups[0])
                self.assertIn("timestamp", backups[0])

    def test_cleanup_old_backups(self):
        """Test cleaning up old backups."""
        # Mock list_backups
        with patch("src.dewey.core.db.backup.list_backups") as mock_list:
            # Create mock backups - one old, one new
            now = datetime.now()
            old_date = (now - timedelta(days=40)).isoformat()
            new_date = (now - timedelta(days=5)).isoformat()

            mock_list.return_value = [
                {
                    "filename": "dewey_backup_old.duckdb",
                    "path": os.path.join(self.temp_dir, "dewey_backup_old.duckdb"),
                    "timestamp": old_date,
                    "size": 1024 * 1024,
                },
                {
                    "filename": "dewey_backup_new.duckdb",
                    "path": os.path.join(self.temp_dir, "dewey_backup_new.duckdb"),
                    "timestamp": new_date,
                    "size": 2 * 1024 * 1024,
                },
            ]

            # Mock os.remove
            with patch("os.remove") as mock_remove:
                # Cleanup backups
                deleted = cleanup_old_backups()

                # Check that only the old backup was deleted
                self.assertEqual(deleted, 1)
                mock_remove.assert_called_once_with(
                    os.path.join(self.temp_dir, "dewey_backup_old.duckdb"),
                )

    def test_verify_backup(self):
        """Test verifying a backup."""
        # Create a mock backup file
        backup_path = os.path.join(self.temp_dir, "backup_test.duckdb")

        # Mock os.path.exists to return True
        self.mock_path_exists.return_value = True

        # Mock connection and execute
        mock_conn = MagicMock()
        self.mock_db_manager.get_connection.return_value = mock_conn

        # Configure mock to return successful results
        mock_conn.execute.return_value = MagicMock()

        # Verify backup
        result = verify_backup(backup_path)

        # Check result
        self.assertTrue(result)

        # Check that get_connection was called
        self.mock_db_manager.get_connection.assert_called_with(backup_path)

        # Check that release_connection was called
        self.mock_db_manager.release_connection.assert_called_with(mock_conn)

    def test_export_table(self):
        """Test exporting a table."""
        # Create output path
        output_path = os.path.join(self.temp_dir, "export.csv")

        # Export table
        export_table("test_table", output_path)

        # Check that database manager was called correctly
        self.mock_db_manager.execute_query.assert_called()

    def test_import_table(self):
        """Test importing a table."""
        # Create input path
        input_path = os.path.join(self.temp_dir, "import.csv")

        # Mock os.path.exists to return True
        self.mock_path_exists.return_value = True

        # Mock result of import query
        self.mock_db_manager.execute_query.return_value = [(10,)]  # 10 rows imported

        # Import table
        result = import_table("test_table", input_path)

        # Check result
        self.assertEqual(result, 10)

        # Check that database manager was called correctly
        self.mock_db_manager.execute_query.assert_called()


if __name__ == "__main__":
    unittest.main()
