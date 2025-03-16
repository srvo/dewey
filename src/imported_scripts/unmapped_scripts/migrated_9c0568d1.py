import base64
import json
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest
import structlog
from email_processing.gmail_client import GmailClient
from google.oauth2 import service_account


@pytest.fixture
def mock_service_account_creds():
    """Mock service account credentials."""
    creds = MagicMock(spec=service_account.Credentials)
    creds.with_subject.return_value = creds  # For user impersonation
    return creds


@pytest.fixture
def mock_service():
    """Mock Gmail API service."""
    service = MagicMock()
    messages = service.users().messages()
    messages.list().execute.return_value = {"messages": [{"id": "test_id"}]}
    messages.get().execute.return_value = {
        "id": "test_id",
        "threadId": "thread123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
            ],
            "mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(b"Test body").decode()},
        },
    }
    return service


@pytest.fixture
def gmail_client(tmp_path):
    """Fixture for Gmail client with temporary paths."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    # Create mock service account key file
    service_account_file = config_dir / "service-account.json"
    service_account_data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test_key_id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "test_client_id",
    }
    service_account_file.write_text(json.dumps(service_account_data))

    client = GmailClient(
        service_account_file=str(service_account_file),
        user_email="user@example.com",
        checkpoint_file=str(config_dir / "checkpoint.json"),
    )
    client.logger = structlog.get_logger()
    return client


def test_authentication_success(
    gmail_client,
    mock_service_account_creds,
    mock_service,
) -> None:
    """Test successful authentication with service account."""
    with (
        patch(
            "google.oauth2.service_account.Credentials.from_service_account_file",
            return_value=mock_service_account_creds,
        ),
        patch("googleapiclient.discovery.build", return_value=mock_service),
    ):
        gmail_client.authenticate()

    assert gmail_client.service is not None
    assert gmail_client.authenticated is True
    assert gmail_client.credentials == mock_service_account_creds
    mock_service_account_creds.with_subject.assert_called_once_with("user@example.com")


def test_authentication_failure(gmail_client) -> None:
    """Test authentication failure handling."""
    with (
        patch(
            "google.oauth2.service_account.Credentials.from_service_account_file",
            side_effect=Exception("Auth failed"),
        ),
        pytest.raises(Exception) as exc_info,
    ):
        gmail_client.authenticate()

    assert "Auth failed" in str(exc_info.value)
    assert not gmail_client.authenticated


def test_fetch_emails_with_date_filter(gmail_client, mock_service) -> None:
    """Test fetching emails with date filter."""
    gmail_client.service = mock_service
    test_date = datetime(2024, 1, 1)

    emails = gmail_client.fetch_emails(since=test_date)

    expected_query = f"after:{test_date.strftime('%Y/%m/%d')}"
    mock_service.users().messages().list.assert_called_with(
        userId="me",
        q=expected_query,
        maxResults=100,
    )
    assert len(emails) == 1
    assert emails[0]["id"] == "test_id"
    assert emails[0]["body_text"] == "Test body"


def test_save_checkpoint(gmail_client) -> None:
    """Test checkpoint saving functionality."""
    test_date = datetime(2024, 1, 1)
    expected_data = json.dumps({"timestamp": test_date.isoformat()})

    with patch("builtins.open", mock_open()) as mock_file:
        gmail_client.save_checkpoint(test_date)
        mock_file.assert_called_once_with(gmail_client.checkpoint_file, "w")
        mock_file().write.assert_called_once_with(expected_data)


def test_load_checkpoint(gmail_client) -> None:
    """Test checkpoint loading functionality."""
    test_date = datetime(2024, 1, 1)
    checkpoint_data = {"timestamp": test_date.isoformat()}

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=json.dumps(checkpoint_data))),
    ):
        loaded_date = gmail_client.load_checkpoint()
        assert loaded_date == test_date


def test_error_handling_fetch_emails(gmail_client, mock_service) -> None:
    """Test error handling during email fetching."""
    gmail_client.service = mock_service
    mock_service.users().messages().list.side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        gmail_client.fetch_emails()

    assert "API Error" in str(exc_info.value)


def test_checkpoint_file_error_handling(gmail_client) -> None:
    """Test error handling for checkpoint file operations."""
    # Test load_checkpoint error handling
    assert (
        gmail_client.load_checkpoint() is None
    )  # Should return None if file doesn't exist

    # Test save_checkpoint error handling
    test_date = datetime(2024, 1, 1)
    with patch("builtins.open", side_effect=OSError("Test error")):
        with pytest.raises(OSError) as exc_info:
            gmail_client.save_checkpoint(test_date)
        assert str(exc_info.value) == "Test error"
