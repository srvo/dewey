import base64
import json
import logging
import os
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

from dewey.core.crm.gmail.gmail_client import GmailClient
from dewey.core.base_script import BaseScript


# Mock BaseScript for testing purposes
class MockBaseScript(BaseScript):
    """Class MockBaseScript."""
    def __init__(self, config_section: Optional[str] = None, requires_db: bool = False, enable_llm: bool = False):
        """Function __init__."""
        super().__init__(config_section=config_section, requires_db=requires_db, enable_llm=enable_llm)

    def run(self) -> None:
        """Function run."""
        pass


@pytest.fixture
def mock_gmail_client(monkeypatch: pytest.MonkeyPatch) -> GmailClient:
    """Fixture to create a GmailClient instance with mocked credentials."""
    # Mock the service_account.Credentials.from_service_account_file method
    mock_creds = MagicMock()
    mock_creds.with_subject.return_value = mock_creds
    monkeypatch.setattr(service_account.Credentials, "from_service_account_file", MagicMock(return_value=mock_creds))

    # Mock the build function
    mock_service = MagicMock()
    monkeypatch.setattr(build, "build", MagicMock(return_value=mock_service))

    # Create a GmailClient instance
    gmail_client = GmailClient(service_account_file="test_service_account.json", user_email="test@example.com")
    return gmail_client


@pytest.fixture
def mock_gmail_service(mock_gmail_client: GmailClient) -> MagicMock:
    """Fixture to return the mocked Gmail service object."""
    return mock_gmail_client.service


@pytest.fixture
def mock_message() -> Dict[str, Any]:
    """Fixture to return a sample email message."""
    return {
        "id": "12345", "threadId": "67890", "labelIds": ["INBOX", "UNREAD"], "snippet": "This is a test email.", "payload": {
            "mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(b"Hello, world!").decode("utf-8")}, }, }


class TestGmailClient:
    """Unit tests for the GmailClient class."""

    def test_init(self) -> None:
        """Test the __init__ method."""
        gmail_client = GmailClient(service_account_file="test_service_account.json", user_email="test@example.com")
        assert gmail_client.service_account_file == "test_service_account.json"
        assert gmail_client.user_email == "test@example.com"
        assert gmail_client.scopes is not None
        assert gmail_client.creds is None
        assert gmail_client.service is None

        gmail_client_no_user = GmailClient(service_account_file="test_service_account.json")
        assert gmail_client_no_user.user_email is None

    @patch("dewey.core.crm.gmail.gmail_client.service_account.Credentials.from_service_account_file")
    @patch("dewey.core.crm.gmail.gmail_client.build")
    def test_authenticate_success(self, mock_build: MagicMock, mock_from_service_account_file: MagicMock) -> None:
        """Test successful authentication."""
        mock_creds = MagicMock()
        mock_creds.with_subject.return_value = mock_creds
        mock_from_service_account_file.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        gmail_client = GmailClient(service_account_file="test_service_account.json", user_email="test@example.com")
        service = gmail_client.authenticate()

        assert service == mock_service
        mock_from_service_account_file.assert_called_once_with(
            gmail_client.service_account_file, scopes=gmail_client.scopes
        )
        mock_creds.with_subject.assert_called_once_with(gmail_client.user_email)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)
        assert gmail_client.service == mock_service

    @patch("dewey.core.crm.gmail.gmail_client.service_account.Credentials.from_service_account_file")
    @patch("dewey.core.crm.gmail.gmail_client.build")
    def test_authenticate_failure(self, mock_build: MagicMock, mock_from_service_account_file: MagicMock) -> None:
        """Test authentication failure."""
        mock_from_service_account_file.side_effect = Exception("Authentication failed")

        gmail_client = GmailClient(service_account_file="test_service_account.json", user_email="test@example.com")
        service = gmail_client.authenticate()

        assert service is None
        assert gmail_client.service is None

    def test_fetch_emails_success(self, mock_gmail_client: GmailClient, mock_gmail_service: MagicMock) -> None:
        """Test successful email fetching."""
        mock_results = {"messages": [{"id": "1"}, {"id": "2"}], "nextPageToken": "next_token"}
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = (
            mock_results
        )

        results = mock_gmail_client.fetch_emails(query="test query", max_results=50, page_token="prev_token")

        assert results == mock_results
        mock_gmail_service.users.return_value.messages.return_value.list.assert_called_once_with(
            userId="me", q="test query", maxResults=50, pageToken="prev_token"
        )

    def test_fetch_emails_http_error(self, mock_gmail_client: GmailClient, mock_gmail_service: MagicMock) -> None:
        """Test email fetching with HTTP error."""
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.side_effect = (
            HttpError(MagicMock(status=404), b"Not Found")
        )

        results = mock_gmail_client.fetch_emails(query="test query", max_results=50, page_token="prev_token")

        assert results is None

    def test_get_message_success(self, mock_gmail_client: GmailClient, mock_gmail_service: MagicMock, mock_message: Dict[str, Any]) -> None:
        """Test successful message retrieval."""
        mock_gmail_service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
            mock_message
        )

        message = mock_gmail_client.get_message(msg_id="12345", format="metadata")

        assert message == mock_message
        mock_gmail_service.users.return_value.messages.return_value.get.assert_called_once_with(
            userId="me", id="12345", format="metadata"
        )

    def test_get_message_http_error(self, mock_gmail_client: GmailClient, mock_gmail_service: MagicMock) -> None:
        """Test message retrieval with HTTP error."""
        mock_gmail_service.users.return_value.messages.return_value.get.return_value.execute.side_effect = (
            HttpError(MagicMock(status=404), b"Not Found")
        )

        message = mock_gmail_client.get_message(msg_id="12345", format="metadata")

        assert message is None

    def test_decode_message_body_success(self, mock_gmail_client: GmailClient, mock_message: Dict[str, Any]) -> None:
        """Test successful message body decoding."""
        decoded_body = mock_gmail_client.decode_message_body(mock_message["payload"]["body"])
        assert decoded_body == "Hello, world!"

    def test_decode_message_body_missing_data(self, mock_gmail_client: GmailClient) -> None:
        """Test message body decoding with missing data."""
        message=None, mock_gmail_client: GmailClient) -> None:
        """Test message body decoding with decoding error."""
        message = {"data": "Invalid base64 string"}
        with patch.object(mock_gmail_client.logger, 'error') as mock_logger:
            decoded_body = mock_gmail_client.decode_message_body(message)
            assert decoded_body == ""
            mock_logger.assert_called_once()

    def test_run(self, mock_gmail_client: GmailClient, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method (placeholder)."""
        with caplog.at_level(logging.INFO):
            if mock_gmail_client: GmailClient) -> None:
        """Test message body decoding with missing data."""
        message is None:
                mock_gmail_client: GmailClient) -> None:
        """Test message body decoding with missing data."""
        message = {"payload": {"body": {}}}
        decoded_body = mock_gmail_client.decode_message_body(message["payload"]["body"])
        assert decoded_body == ""

    def test_decode_message_body_decoding_error(self
            mock_gmail_client.run()
        assert "GmailClient run method called (placeholder)." in caplog.text
