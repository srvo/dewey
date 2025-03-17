
# Refactored from: test_sync_emails
# Date: 2025-03-16T16:19:09.182815
# Refactor Version: 1.0
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command


@pytest.fixture
def mock_imap_sync():
    with patch("email_processing.management.commands.sync_emails.IMAPSync") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.mark.django_db
def test_sync_emails_command(mock_imap_sync, settings) -> None:
    # Configure test settings
    settings.IMAP_USERNAME = "test@example.com"
    settings.IMAP_PASSWORD = "password123"

    # Run command
    call_command("sync_emails")

    # Verify IMAP sync was initialized and run correctly
    mock_imap_sync.initialize.assert_called_once_with("test@example.com", "password123")
    mock_imap_sync.sync_folder.assert_called_once_with("INBOX")
    mock_imap_sync.close.assert_called_once()


@pytest.mark.django_db
def test_sync_emails_command_with_args(mock_imap_sync) -> None:
    # Run command with custom arguments
    call_command(
        "sync_emails",
        username="custom@example.com",
        password="custom123",
        folder="Sent",
    )

    # Verify IMAP sync was initialized and run with custom args
    mock_imap_sync.initialize.assert_called_once_with("custom@example.com", "custom123")
    mock_imap_sync.sync_folder.assert_called_once_with("Sent")
    mock_imap_sync.close.assert_called_once()


@pytest.mark.django_db
def test_sync_emails_command_error_handling(mock_imap_sync) -> None:
    # Setup mock to raise an exception
    mock_imap_sync.sync_folder.side_effect = Exception("IMAP error")

    # Verify command handles error
    with pytest.raises(Exception) as exc:
        call_command("sync_emails")

    assert str(exc.value) == "IMAP error"
    mock_imap_sync.close.assert_called_once()
