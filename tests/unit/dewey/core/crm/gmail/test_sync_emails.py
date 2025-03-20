import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.crm.gmail.sync_emails import SyncEmails


class TestSyncEmails:
    """Unit tests for the SyncEmails class."""

    @pytest.fixture
    def sync_emails(self) -> SyncEmails:
        """Fixture to create a SyncEmails instance with mocked dependencies."""
        sync_emails = SyncEmails()
        sync_emails.logger = MagicMock(spec=logging.Logger)
        sync_emails.db_conn = MagicMock()
        sync_emails.get_config_value = MagicMock(return_value="test_value")
        return sync_emails

    def test_init(self, sync_emails: SyncEmails) -> None:
        """Test the __init__ method."""
        assert sync_emails.config_section == "gmail_sync"
        assert sync_emails.requires_db is True
        assert sync_emails.name == "SyncEmails"

    def test_run_success(self, sync_emails: SyncEmails) -> None:
        """Test the run method when email synchronization completes successfully."""
        sync_emails.run()
        sync_emails.logger.info.assert_called_with("Email synchronization completed successfully")

    def test_run_exception(self, sync_emails: SyncEmails) -> None:
        """Test the run method when an exception occurs during synchronization."""
        sync_emails.logger.info.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            sync_emails.run()

        sync_emails.logger.error.assert_called()
