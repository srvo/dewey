"""Unit tests for Gmail client functionality."""

import base64
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import structlog
from email_processing.gmail_client import SCOPES, GmailClient
from googleapiclient.errors import HttpError


class MockCredentials:
    """Mock implementation of Google OAuth2 credentials."""

    def __init__(self, valid: bool = True, expired: bool = False) -> None:
        """Initializes MockCredentials."""
        self.token: str = "test_token"
        self.refresh_token: str = "test_refresh_token"
        self.token_uri: str = "https://oauth2.googleapis.com/token"
        self.client_id: str = "test_client_id"
        self.client_secret: str = "test_client_secret"
        self.scopes: list[str] = SCOPES
        self.valid: bool = valid
        self.expired: bool = expired
        self.refresh_called: bool = False

    def refresh(self, request: MagicMock) -> None:
        """Mock token refresh."""
        self.refresh_called = True
        self.expired = False
        self.valid = True

    def authorize(self, http: MagicMock) -> MagicMock:
        """Mock authorize method required by google-api-python-client."""
        return http

    def to_json(self) -> str:
        """Mock JSON serialization."""
        return json.dumps(
            {
                "token": self.token,
                "refresh_token": self.refresh_token,
                "token_uri": self.token_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scopes": self.scopes,
            },
        )


@pytest.fixture
def mock_credentials() -> MockCredentials:
    """Fixture for OAuth2 credentials."""
    return MockCredentials()


@pytest.fixture
def test_credentials_file(tmp_path: Path) -> Path:
    """Create a test credentials file."""
    creds_data: dict[str, Any] = {
        "installed": {
            "client_id": "test_client_id",
            "project_id": "test-project",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "test_client_secret",
            "redirect_uris": ["http://localhost"],
        },
    }
    creds_file: Path = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps(creds_data))
    return creds_file


@pytest.fixture
def mock_email_data() -> dict[str, Any]:
    """Fixture for sample email data."""
    return {
        "id": "test_id",
        "threadId": "thread123",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {
                    "name": "To",
                    "value": "recipient1@example.com,recipient2@example.com",
                },
                {"name": "Date", "value": "Tue, 16 Jan 2024 00:00:00 +0000"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(b"Test plain body").decode(),
                    },
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            b"<p>Test HTML body</p>",
                        ).decode(),
                    },
                },
            ],
        },
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Test email snippet",
    }


@pytest.fixture
def mock_service() -> MagicMock:
    """Fixture for Gmail API service."""
    service: MagicMock = MagicMock()
    messages: MagicMock = service.users().messages()
    messages.list().execute.return_value = {"messages": [{"id": "test_id"}]}
    messages.get().execute.return_value = {}
    service.users().labels().list().execute.return_value = {
        "labels": [
            {"id": "INBOX", "name": "INBOX"},
            {"id": "UNREAD", "name": "UNREAD"},
        ],
    }
    return service


@pytest.fixture
def gmail_client(tmp_path: Path, test_credentials_file: Path) -> GmailClient:
    """Fixture for Gmail client with temporary paths."""
    client: GmailClient = GmailClient()
    client.credentials_file = test_credentials_file
    client.token_file = tmp_path / "token.pickle"
    client.checkpoint_file = tmp_path / "checkpoint.pickle"
    client.logger = structlog.get_logger()
    return client


class TestGmailClientAuthentication:
    """Tests for Gmail client authentication functionality."""

    def test_authentication_success(
        self,
        gmail_client: GmailClient,
        mock_credentials: MockCredentials,
        mock_service: MagicMock,
    ) -> None:
        """Test successful authentication with valid credentials."""
        with (
            patch("pickle.load", return_value=mock_credentials),
            patch("googleapiclient.discovery.build", return_value=mock_service),
        ):
            gmail_client.authenticate()

        assert gmail_client.service is not None
        assert gmail_client.authenticated is True
        assert gmail_client.credentials == mock_credentials

    def test_token_refresh(
        self,
        gmail_client: GmailClient,
        mock_service: MagicMock,
    ) -> None:
        """Test token refresh for expired credentials."""
        expired_creds: MockCredentials = MockCredentials(valid=False, expired=True)

        with (
            patch("pickle.load", return_value=expired_creds),
            patch("googleapiclient.discovery.build", return_value=mock_service),
            patch("google.auth.transport.requests.Request"),
        ):
            gmail_client.authenticate()

        assert expired_creds.refresh_called
        assert not expired_creds.expired
        assert expired_creds.valid
        assert gmail_client.service is not None

    def test_new_authentication_flow(
        self,
        gmail_client: GmailClient,
        mock_credentials: MockCredentials,
        mock_service: MagicMock,
    ) -> None:
        """Test new authentication flow when no token exists."""
        with (
            patch("pickle.load", side_effect=FileNotFoundError),
            patch(
                "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
            ) as mock_flow,
            patch("googleapiclient.discovery.build", return_value=mock_service),
        ):
            mock_flow.return_value.run_local_server.return_value = mock_credentials
            gmail_client.authenticate()

        mock_flow.assert_called_once_with(str(gmail_client.credentials_file), SCOPES)
        assert gmail_client.service is not None
        assert gmail_client.authenticated

    def test_authentication_invalid_credentials(
        self,
        gmail_client: GmailClient,
    ) -> None:
        """Test authentication with invalid credentials file."""
        with (
            patch("pickle.load", side_effect=FileNotFoundError),
            patch(
                "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
                side_effect=FileNotFoundError("Credentials file not found"),
            ),
            pytest.raises(FileNotFoundError),
        ):
            gmail_client.authenticate()


class TestGmailClientEmailOperations:
    """Tests for Gmail client email operations."""

    def test_fetch_emails_success(
        self,
        gmail_client: GmailClient,
        mock_service: MagicMock,
        mock_email_data: dict[str, Any],
    ) -> None:
        """Test successful email fetching."""
        gmail_client.service = mock_service
        mock_service.users().messages().get().execute.return_value = mock_email_data

        emails: list[dict[str, Any]] = gmail_client.fetch_emails(max_results=1)

        assert len(emails) == 1
        assert emails[0]["id"] == "test_id"
        assert emails[0]["subject"] == "Test Subject"

    def test_fetch_emails_with_date_filter(
        self,
        gmail_client: GmailClient,
        mock_service: MagicMock,
        mock_email_data: dict[str, Any],
    ) -> None:
        """Test fetching emails with date filter."""
        gmail_client.service = mock_service
        mock_service.users().messages().get().execute.return_value = mock_email_data
        test_date: datetime = datetime(2024, 1, 1)

        gmail_client.fetch_emails(since=test_date)

        expected_query: str = f"after:{test_date.strftime('%Y/%m/%d')}"
        mock_service.users().messages().list.assert_called_with(
            userId="me",
            q=expected_query,
            maxResults=100,
        )

    def test_fetch_emails_error_handling(
        self,
        gmail_client: GmailClient,
        mock_service: MagicMock,
    ) -> None:
        """Test error handling during email fetching."""
        gmail_client.service = mock_service
        mock_service.users().messages().list.side_effect = HttpError(
            resp=MagicMock(status=403),
            content=b'{"error": "forbidden"}',
        )

        with pytest.raises(HttpError) as exc_info:
            gmail_client.fetch_emails()

        assert exc_info.value.resp.status == 403

    def test_parse_email_complete(
        self,
        gmail_client: GmailClient,
        mock_email_data: dict[str, Any],
    ) -> None:
        """Test complete email parsing with all fields."""
        parsed: dict[str, Any] = gmail_client._parse_email(mock_email_data)

        assert parsed["id"] == "test_id"
        assert parsed["subject"] == "Test Subject"
        assert parsed["from"] == "sender@example.com"
        assert parsed["to"] == ["recipient1@example.com", "recipient2@example.com"]
        assert parsed["body_text"] == "Test plain body"
        assert parsed["body_html"] == "<p>Test HTML body</p>"
        assert parsed["labels"] == ["INBOX", "UNREAD"]

    def test_parse_email_minimal(self, gmail_client: GmailClient) -> None:
        """Test parsing email with minimal fields."""
        minimal_email: dict[str, Any] = {
            "id": "test_id",
            "threadId": "thread123",
            "payload": {"mimeType": "text/plain", "headers": [], "body": {"data": ""}},
            "snippet": "",
        }

        parsed: dict[str, Any] = gmail_client._parse_email(minimal_email)

        assert parsed["id"] == "test_id"
        assert parsed["subject"] == ""
        assert parsed["from"] == ""
        assert parsed["to"] == []
        assert parsed["body_text"] == ""
        assert parsed["body_html"] == ""
        assert parsed["labels"] == []


class TestGmailClientCheckpointing:
    """Tests for Gmail client checkpointing functionality."""

    def test_checkpoint_save_load(
        self,
        gmail_client: GmailClient,
        tmp_path: Path,
    ) -> None:
        """Test saving and loading checkpoint."""
        test_date: datetime = datetime(2024, 1, 1)

        # Save checkpoint
        gmail_client.save_checkpoint(test_date)
        assert gmail_client.checkpoint_file.exists()

        # Load checkpoint
        loaded_date: datetime | None = gmail_client.load_checkpoint()
        assert loaded_date == test_date

    def test_checkpoint_file_error_handling(self, gmail_client: GmailClient) -> None:
        """Test checkpoint file error handling."""
        # Test loading non-existent checkpoint
        assert gmail_client.load_checkpoint() is None

        # Test loading corrupted checkpoint
        with patch("pickle.load", side_effect=pickle.PickleError):
            assert gmail_client.load_checkpoint() is None

    def test_checkpoint_save_error_handling(self, gmail_client: GmailClient) -> None:
        """Test checkpoint save error handling."""
        test_date: datetime = datetime(2024, 1, 1)

        with (
            patch("builtins.open", side_effect=OSError("Test error")),
            pytest.raises(OSError),
        ):
            gmail_client.save_checkpoint(test_date)
