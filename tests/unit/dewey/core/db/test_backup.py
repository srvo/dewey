import logging
from unittest.mock import patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.db.backup import Backup


class TestBackup:
    """Tests for the Backup class."""

    @pytest.fixture
    def mock_backup_database(self):
        """Mocks the backup_database function."""
        with patch("dewey.core.db.backup.backup_database") as mock:
            yield mock

    @pytest.fixture
    def mock_restore_database(self):
        """Mocks the restore_database function."""
        with patch("dewey.core.db.backup.restore_database") as mock:
            yield mock

    @pytest.fixture
    def backup_instance(self):
        """Returns a Backup instance with mocked dependencies."""
        with patch.object(BaseScript, "__init__", return_value=None):
            backup = Backup()
            backup.logger = logging.getLogger(__name__)  # Mock logger
            backup.config = {
                "backup": {
                    "backup_location": "/tmp/backup",
                    "restore_location": "/tmp/restore",
                },
                "core": {"database": {}},
            }  # Mock config
            backup.db_conn = "mock_db_conn"  # Mock db_conn
            return backup

    def test_init(self):
        """Test the __init__ method."""
        with patch.object(BaseScript, "__init__") as mock_init:
            Backup(config_section="test_config")
            mock_init.assert_called_once_with(
                config_section="test_config", requires_db=True
            )

    def test_run(self, backup_instance, mock_backup_database):
        """Test the run method."""
        backup_instance.run()
        backup_instance.logger.info.assert_called()
        mock_backup_database.assert_called_once_with(
            "mock_db_conn", "/tmp/backup", backup_instance.logger
        )

    def test_run_default_location(self):
        """Test the run method with default backup location."""
        with patch.object(BaseScript, "__init__", return_value=None):
            backup = Backup()
            backup.logger = logging.getLogger(__name__)  # Mock logger
            backup.config = {"backup": {}, "core": {"database": {}}}  # Mock config
            backup.db_conn = "mock_db_conn"  # Mock db_conn
            with patch("dewey.core.db.backup.backup_database") as mock_backup_database:
                backup.run()
                mock_backup_database.assert_called_once_with(
                    "mock_db_conn", "/default/backup/path", backup.logger
                )

    def test_restore(self, backup_instance, mock_restore_database):
        """Test the restore method."""
        backup_instance.restore()
        backup_instance.logger.info.assert_called()
        mock_restore_database.assert_called_once_with(
            "mock_db_conn", "/tmp/restore", backup_instance.logger
        )

    def test_restore_default_location(self):
        """Test the restore method with default restore location."""
        with patch.object(BaseScript, "__init__", return_value=None):
            backup = Backup()
            backup.logger = logging.getLogger(__name__)  # Mock logger
            backup.config = {"backup": {}, "core": {"database": {}}}  # Mock config
            backup.db_conn = "mock_db_conn"  # Mock db_conn
            with patch("dewey.core.db.backup.restore_database") as mock_restore_database:
                backup.restore()
                mock_restore_database.assert_called_once_with(
                    "mock_db_conn", "/default/restore/path", backup.logger
                )

    def test_backup_database_success(self, backup_instance, mock_backup_database):
        """Test the _backup_database method with success."""
        backup_instance._backup_database("/tmp/backup")
        mock_backup_database.assert_called_once_with(
            "mock_db_conn", "/tmp/backup", backup_instance.logger
        )

    def test_backup_database_failure(self, backup_instance, mock_backup_database):
        """Test the _backup_database method with failure."""
        mock_backup_database.side_effect = Exception("Backup failed")
        with pytest.raises(Exception, match="Backup failed"):
            backup_instance._backup_database("/tmp/backup")
        backup_instance.logger.error.assert_called()

    def test_restore_database_success(self, backup_instance, mock_restore_database):
        """Test the _restore_database method with success."""
        backup_instance._restore_database("/tmp/restore")
        mock_restore_database.assert_called_once_with(
            "mock_db_conn", "/tmp/restore", backup_instance.logger
        )

    def test_restore_database_failure(self, backup_instance, mock_restore_database):
        """Test the _restore_database method with failure."""
        mock_restore_database.side_effect = Exception("Restore failed")
        with pytest.raises(Exception, match="Restore failed"):
            backup_instance._restore_database("/tmp/restore")
        backup_instance.logger.error.assert_called()
