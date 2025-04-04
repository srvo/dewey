"""
Integration tests for database CLI commands.
"""

import unittest
from unittest.mock import patch
import typer
from typer.testing import CliRunner

from src.dewey.cli.db import app
from src.dewey.core.db.operations import DatabaseMaintenance

runner = CliRunner()

class TestDatabaseCLI(unittest.TestCase):
    """Test database CLI commands."""

    @patch("src.dewey.cli.db.DatabaseMaintenance")
    def test_cleanup_tables(self, mock_maint):
        """Test cleanup-tables command."""
        # Setup mock
        mock_instance = mock_maint.return_value
        
        # Run command
        result = runner.invoke(
            app,
            ["cleanup-tables", "table1", "table2", "--dry-run"]
        )
        
        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_maint.assert_called_once_with(config=None, dry_run=True)
        mock_instance.cleanup_tables.assert_called_once_with(["table1", "table2"])

    @patch("src.dewey.cli.db.DatabaseMaintenance")
    def test_analyze_tables(self, mock_maint):
        """Test analyze-tables command."""
        # Setup mock
        mock_instance = mock_maint.return_value
        mock_instance.analyze_tables.return_value = {
            "table1": {"row_count": 100, "size_bytes": 1024}
        }
        
        # Run command
        result = runner.invoke(
            app,
            ["analyze-tables", "table1"]
        )
        
        # Verify
        self.assertEqual(result.exit_code, 0)
        self.assertIn("table1", result.output)
        self.assertIn("Rows: 100", result.output)
        self.assertIn("Size: 1024 bytes", result.output)

    @patch("src.dewey.cli.db.DatabaseMaintenance")
    def test_force_cleanup(self, mock_maint):
        """Test force-cleanup command."""
        # Setup mock
        mock_instance = mock_maint.return_value
        
        # Run command
        result = runner.invoke(
            app,
            ["force-cleanup", "--dry-run"]
        )
        
        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_maint.assert_called_once_with(config=None, dry_run=True)
        mock_instance.force_cleanup.assert_called_once()

    @patch("src.dewey.cli.db.DatabaseMaintenance")
    def test_upload_db(self, mock_maint):
        """Test upload-db command."""
        # Setup mock
        mock_instance = mock_maint.return_value
        
        # Run command
        result = runner.invoke(
            app,
            ["upload-db", "test_db", "--destination", "remote"]
        )
        
        # Verify
        self.assertEqual(result.exit_code, 0)
        mock_maint.assert_called_once_with(config=None, dry_run=False)
        mock_instance.upload_database.assert_called_once_with("test_db", "remote")

    def test_missing_args(self):
        """Test missing required arguments."""
        # Test missing tables for cleanup
        result = runner.invoke(app, ["cleanup-tables"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: No tables specified", result.output)
        
        # Test missing destination for upload
        result = runner.invoke(app, ["upload-db", "test_db"])
        self.assertEqual(result.exit_code, 2)  # Typer exits with 2 for missing options

if __name__ == "__main__":
    unittest.main()