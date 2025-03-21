"""Tests for the CRM communication module."""

import email
import imaplib
from unittest.mock import MagicMock, Mock, patch

import pytest

from dewey.core.crm.communication.email_client import EmailClient


class TestEmailClient:
    """Test suite for the EmailClient class."""

    def test_initialization(self) -> None:
        """Test EmailClient initialization."""
        with patch.object(EmailClient, '_setup_gmail') as mock_setup:
            client = EmailClient()
            assert client is not None
            assert client.provider == "gmail"
            assert client.config_section == "email_client"
            assert client.requires_db is True
            mock_setup.assert_called_once()

    def test_initialization_with_imap(self) -> None:
        """Test EmailClient initialization with IMAP provider."""
        with patch.object(EmailClient, '_setup_imap') as mock_setup:
            client = EmailClient(provider="generic_imap")
            assert client is not None
            assert client.provider == "generic_imap"
            mock_setup.assert_called_once()

    @patch('imaplib.IMAP4_SSL')
    def test_setup_imap(self, mock_imap) -> None:
        """Test IMAP setup."""
        mock_imap_instance = MagicMock()
        mock_imap.return_value = mock_imap_instance

        # Create a client with _setup_imap patched out to avoid connection attempts
        with patch.object(EmailClient, '_setup_imap'):
            client = EmailClient()
        
        # Manually configure client for testing
        client.config = {
            "email_client": {
                "imap_server": "imap.test.com",
                "imap_port": "993",
                "email_username": "test@example.com",
                "email_password": "test_password"
            }
        }
        
        # Call setup method directly
        client._setup_imap()
        
        # Verify
        mock_imap.assert_called_with("imap.test.com", 993)
        mock_imap_instance.login.assert_called_with("test@example.com", "test_password")

    @patch('imaplib.IMAP4_SSL')
    def test_fetch_emails_imap(self, mock_imap) -> None:
        """Test fetching emails via IMAP."""
        # Setup mock IMAP
        mock_imap_instance = MagicMock()
        mock_imap.return_value = mock_imap_instance
        
        # Create a properly patched client to avoid real connections
        with patch.object(EmailClient, '_setup_gmail'), patch.object(EmailClient, '_setup_imap'):
            client = EmailClient()
        
        # Mock search and fetch responses
        mock_imap_instance.search.return_value = ("OK", [b"1 2 3"])
        
        # Create a mock email message
        mock_email = email.message.Message()
        mock_email["Subject"] = "Test Subject"
        mock_email["From"] = "Test User <test@example.com>"
        mock_email["To"] = "recipient@example.com"
        mock_email["Date"] = "Thu, 1 Jan 2023 12:00:00 +0000"
        mock_email_bytes = mock_email.as_bytes()
        
        # Setup the fetch response for each email ID
        mock_imap_instance.fetch.side_effect = [
            ("OK", [(b"1", mock_email_bytes)]),
            ("OK", [(b"2", mock_email_bytes)]),
            ("OK", [(b"3", mock_email_bytes)])
        ]
        
        # Set the mock connection
        client.imap_conn = mock_imap_instance
        
        # Call the method
        emails = client._fetch_emails_imap("INBOX", 10)
        
        # Verify
        mock_imap_instance.select.assert_called_with("INBOX")
        mock_imap_instance.search.assert_called_once()
        # Check that fetch was called 3 times (once for each email ID)
        assert mock_imap_instance.fetch.call_count == 3
        assert len(emails) == 3

    def test_decode_header(self) -> None:
        """Test decoding email headers."""
        # Create a client with patches to avoid real connections
        with patch.object(EmailClient, '_setup_gmail'), patch.object(EmailClient, '_setup_imap'):
            client = EmailClient()
        
        # Test simple header
        result = client._decode_header("Simple Header")
        assert result == "Simple Header"
        
        # Test encoded header
        encoded_header = "=?utf-8?q?Test=20Header?="
        result = client._decode_header(encoded_header)
        assert "Test Header" in result

    def test_parse_email_header(self) -> None:
        """Test parsing email headers."""
        # Create a client with patches to avoid real connections
        with patch.object(EmailClient, '_setup_gmail'), patch.object(EmailClient, '_setup_imap'):
            client = EmailClient()
        
        # Test with name and email
        name, email_address = client._parse_email_header("John Doe <john@example.com>")
        assert name == "John Doe"
        assert email_address == "john@example.com"
        
        # Test with quoted name
        name, email_address = client._parse_email_header('"Doe, John" <john@example.com>')
        assert name == "Doe, John"
        assert email_address == "john@example.com"
        
        # Test with just email
        name, email_address = client._parse_email_header("john@example.com")
        assert name == ""
        assert email_address == "john@example.com"

    @patch('dewey.core.db.connection.get_connection')
    def test_save_emails_to_db(self, mock_get_connection) -> None:
        """Test saving emails to the database."""
        # Create a client with patches to avoid real connections
        with patch.object(EmailClient, '_setup_gmail'), patch.object(EmailClient, '_setup_imap'):
            client = EmailClient()
        
        # Setup
        mock_db = MagicMock()
        mock_get_connection.return_value = mock_db
        client.db_conn = mock_db
        
        emails = [
            {
                "email_id": "123",
                "subject": "Test Subject",
                "from_name": "John Doe",
                "from_email": "john@example.com",
                "to": "recipient@example.com",
                "date": "2023-01-01 12:00:00",
                "body_text": "Test body",
                "body_html": "<p>Test body</p>",
                "has_attachments": False
            }
        ]
        
        # Execute
        client.save_emails_to_db(emails)
        
        # Verify
        assert mock_db.execute.call_count >= 2  # One for CREATE TABLE, one for INSERT
        mock_db.commit.assert_called_once()

    def test_close(self) -> None:
        """Test closing connections."""
        # Create a client with patches to avoid real connections
        with patch.object(EmailClient, '_setup_gmail'), patch.object(EmailClient, '_setup_imap'):
            client = EmailClient()
        
        mock_imap = MagicMock()
        client.imap_conn = mock_imap
        
        client.close()
        
        mock_imap.close.assert_called_once()
        mock_imap.logout.assert_called_once()
        assert client.imap_conn is None 