import unittest
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.db.migrations import Migrations


class TestMigrations(unittest.TestCase):
    """Class TestMigrations."""

    def setUp(self):
        """Setup method to create a Migrations instance before each test."""
        self.migrations = Migrations()
        self.migrations.logger = MagicMock()  # Mock the logger
        self.migrations.db_conn = MagicMock()  # Mock the db_conn

    def test_init(self):
        """Test the __init__ method of the Migrations class."""
        self.assertEqual(self.migrations.config_section, "migrations")
        self.assertTrue(self.migrations.requires_db)

    @patch("dewey.core.db.migrations.utils.table_exists")
    @patch("dewey.core.db.migrations.utils.create_table")
    def test_run_success(self, mock_create_table, mock_table_exists):
        """Test the run method with successful migration execution."""
        mock_table_exists.return_value = False
        self.migrations.get_config_value = MagicMock(return_value="localhost")

        self.migrations.run()

        self.migrations.logger.info.assert_called_with(
            "Database migrations ran successfully."
        )
        mock_create_table.assert_called_once()

    @patch("dewey.core.db.migrations.utils.table_exists")
    def test_run_table_exists(self, mock_table_exists):
        """Test the run method when the table already exists."""
        mock_table_exists.return_value = True
        self.migrations.get_config_value = MagicMock(return_value="localhost")

        self.migrations.run()

        self.migrations.logger.info.assert_called_with(
            "Table example_table already exists"
        )

    @patch("dewey.core.db.migrations.utils.table_exists")
    @patch("dewey.core.db.migrations.utils.create_table")
    def test_run_exception(self, mock_create_table, mock_table_exists):
        """Test the run method when an exception occurs during migration."""
        mock_table_exists.return_value = False
        mock_create_table.side_effect = Exception("Test exception")
        self.migrations.get_config_value = MagicMock(return_value="localhost")

        with self.assertRaises(Exception) as context:
            self.migrations.run()

        self.assertEqual(str(context.exception), "Test exception")
        self.migrations.logger.error.assert_called()

    def test_run_db_host_config(self):
        """Test that the db_host config value is logged."""
        self.migrations.get_config_value = MagicMock(return_value="test_host")
        with patch("dewey.core.db.migrations.utils.table_exists") as mock_table_exists:
            mock_table_exists.return_value = True
            self.migrations.run()
        self.migrations.logger.info.assert_any_call("Database host: test_host")
