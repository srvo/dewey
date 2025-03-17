
# Refactored from: test_imap_sync
# Date: 2025-03-16T16:19:10.638969
# Refactor Version: 1.0
import email
from datetime import datetime
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from email_processing.imap_sync import IMAPSync
from email_processing.models import Email, RawEmail


@pytest.fixture
def mock_imap_client():
    """Create a mock IMAP client."""
    with patch("email_processing.imap_sync.IMAPClient") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance

        # Setup basic responses
        client_instance.login.return_value = True
        client_instance.select_folder.return_value = True

        yield client_instance


@pytest.fixture
def test_email_message():
    """Create a test email message."""
    msg = MIMEText("Test message body")
    msg["Subject"] = "Test Subject"
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Message-ID"] = "<test123@example.com>"
    msg["Date"] = email.utils.formatdate()
    return msg


@pytest.fixture
def mock_new_email_response():
    """Create a mock email response for new email test."""
    return {
        1: {
            b"FLAGS": (b"\\Seen",),
            b"INTERNALDATE": b"17-Jan-2025 14:07:32 +0000",
            b"RFC822": (
                b'Content-Type: text/plain; charset="utf-8"\n'
                b"MIME-Version: 1.0\n"
                b"Content-Transfer-Encoding: 7bit\n"
                b"Subject: Test Subject\n"
                b"From: sender@example.com\n"
                b"To: recipient@example.com\n"
                b"Message-ID: <test123@example.com>\n"
                b"Date: Fri, 17 Jan 2025 21:07:32 -0000\n\n"
                b"Test message body"
            ),
        },
    }


@pytest.fixture
def mock_existing_email_response():
    """Create a mock email response for existing email test."""
    return {
        1: {
            b"FLAGS": (b"\\Seen",),
            b"INTERNALDATE": b"17-Jan-2025 14:07:32 +0000",
            b"RFC822": (
                b'Content-Type: text/plain; charset="utf-8"\n'
                b"MIME-Version: 1.0\n"
                b"Content-Transfer-Encoding: 7bit\n"
                b"Subject: Test Subject\n"
                b"From: sender@example.com\n"
                b"To: recipient@example.com\n"
                b"Message-ID: <existing123@example.com>\n"
                b"Date: Fri, 17 Jan 2025 21:07:32 -0000\n\n"
                b"Test message body"
            ),
        },
    }


def test_initialize_connection(mock_imap_client) -> None:
    """Test IMAP connection initialization."""
    sync = IMAPSync()
    sync.initialize("test@example.com", "password")

    mock_imap_client.login.assert_called_once_with("test@example.com", "password")
    assert sync.client == mock_imap_client


def test_sync_folder_new_email(mock_imap_client, mock_new_email_response) -> None:
    """Test syncing a new email from IMAP folder."""
    # Setup mock responses
    mock_imap_client.search.return_value = [1]
    mock_imap_client.fetch.return_value = mock_new_email_response

    # Initialize and sync
    sync = IMAPSync()
    sync.client = mock_imap_client
    sync.sync_folder("INBOX")

    # Verify folder was selected
    mock_imap_client.select_folder.assert_called_once_with("INBOX")

    # Verify email was created
    email = Email.objects.get(message_id="<test123@example.com>")
    assert email.subject == "Test Subject"
    assert email.from_email == "sender@example.com"
    assert email.to_emails == ["recipient@example.com"]
    assert email.is_read is True

    # Verify raw email was stored
    raw_email = RawEmail.objects.get(email=email)
    assert raw_email.raw_data == mock_new_email_response[1][b"RFC822"]


def test_sync_folder_existing_email(
    mock_imap_client,
    mock_existing_email_response,
) -> None:
    """Test syncing an existing email from IMAP folder."""
    # Create existing email
    Email.objects.create(
        message_id="<existing123@example.com>",
        subject="Old Subject",
        from_email="old@example.com",
        to_emails=["old@example.com"],
        received_at=timezone.make_aware(datetime(2025, 1, 17, 21, 7, 32)),
    )

    # Setup mock responses
    mock_imap_client.search.return_value = [1]
    mock_imap_client.fetch.return_value = mock_existing_email_response

    # Initialize and sync
    sync = IMAPSync()
    sync.client = mock_imap_client
    sync.sync_folder("INBOX")

    # Verify folder was selected
    mock_imap_client.select_folder.assert_called_once_with("INBOX")

    # Verify email was updated
    updated_email = Email.objects.get(message_id="<existing123@example.com>")
    assert updated_email.subject == "Test Subject"
    assert updated_email.from_email == "sender@example.com"
    assert updated_email.to_emails == ["recipient@example.com"]
    assert updated_email.is_read is True


def test_sync_folder_error_handling(mock_imap_client) -> None:
    """Test error handling during folder sync."""
    mock_imap_client.search.side_effect = Exception("IMAP error")

    sync = IMAPSync()
    sync.client = mock_imap_client

    with pytest.raises(Exception) as exc:
        sync.sync_folder("INBOX")

    assert str(exc.value) == "IMAP error"


def test_close_connection(mock_imap_client) -> None:
    """Test closing IMAP connection."""
    sync = IMAPSync()
    sync.client = mock_imap_client
    sync.close()

    mock_imap_client.logout.assert_called_once()
