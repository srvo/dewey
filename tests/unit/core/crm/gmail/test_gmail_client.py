"""Tests for the Gmail client module."""

import json
from unittest.mock import patch, MagicMock
import pytest
from dewey.core.crm.gmail.gmail_client import GmailClient


def test_gmail_client_init():
    """Test GmailClient initialization."""
    client = GmailClient(
        service_account_file="/path/to/credentials.json", user_email="test@example.com"
    )

    assert client.service_account_file.name == "credentials.json"
    assert client.user_email == "test@example.com"
    assert client.scopes == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert client.creds is None
    assert client.service is None


@patch("dewey.core.crm.gmail.gmail_client.service_account.Credentials")
@patch("dewey.core.crm.gmail.gmail_client.build")
def test_authenticate_success(mock_build, mock_creds_class):
    """Test successful authentication."""
    # Setup mocks
    mock_creds = MagicMock()
    mock_creds_class.from_service_account_file.return_value = mock_creds
    mock_creds.with_subject.return_value = mock_creds
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Create client and authenticate
    client = GmailClient(
        service_account_file="/path/to/credentials.json", user_email="test@example.com"
    )
    result = client.authenticate()

    # Verify
    assert result == mock_service
    assert client.creds == mock_creds
    assert client.service == mock_service
    mock_creds_class.from_service_account_file.assert_called_once_with(
        client.service_account_file, scopes=client.scopes
    )
    mock_creds.with_subject.assert_called_once_with("test@example.com")
    mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)


@patch("dewey.core.crm.gmail.gmail_client.service_account.Credentials")
def test_authenticate_failure(mock_credentials):
    """Test authentication failure."""
    # Setup mock to raise an exception
    mock_credentials.from_service_account_file.side_effect = Exception("Auth failed")

    # Create client and attempt authentication
    client = GmailClient(
        service_account_file="/path/to/credentials.json", user_email="test@example.com"
    )
    result = client.authenticate()

    # Verify
    assert result is None
    assert client.creds is None
    assert client.service is None


def test_fetch_emails_success(mock_gmail_service, sample_email_batch):
    """Test successful email fetching."""
    # Setup mock service
    mock_response = {"messages": sample_email_batch, "nextPageToken": "token123"}
    mock_service = mock_gmail_service([({"status": "200"}, json.dumps(mock_response))])

    # Create client and set service
    client = GmailClient(service_account_file="/path/to/credentials.json")
    client.service = mock_service

    # Fetch emails
    result = client.fetch_emails(query="in:inbox", max_results=5)

    # Verify
    assert result == mock_response
    assert len(result["messages"]) == 5
    assert result["nextPageToken"] == "token123"


def test_fetch_emails_error(mock_gmail_service):
    """Test email fetching with API error."""
    # Setup mock service to return an error
    mock_service = mock_gmail_service([({"status": "400"}, "Bad Request")])

    # Create client and set service
    client = GmailClient(service_account_file="/path/to/credentials.json")
    client.service = mock_service

    # Fetch emails
    result = client.fetch_emails()

    # Verify
    assert result is None


def test_get_message_success(mock_gmail_service, sample_email_data):
    """Test successful message retrieval."""
    # Setup mock service
    mock_service = mock_gmail_service(
        [({"status": "200"}, json.dumps(sample_email_data))]
    )

    # Create client and set service
    client = GmailClient(service_account_file="/path/to/credentials.json")
    client.service = mock_service

    # Get message
    result = client.get_message("msg123")

    # Verify
    assert result == sample_email_data
    assert result["id"] == "msg123"


def test_get_message_error(mock_gmail_service):
    """Test message retrieval with API error."""
    # Setup mock service to return an error
    mock_service = mock_gmail_service([({"status": "404"}, "Not Found")])

    # Create client and set service
    client = GmailClient(service_account_file="/path/to/credentials.json")
    client.service = mock_service

    # Get message
    result = client.get_message("msg123")

    # Verify
    assert result is None


def test_decode_message_body():
    """Test message body decoding."""
    client = GmailClient(service_account_file="/path/to/credentials.json")

    # Test valid message
    message = {"data": "SGVsbG8gV29ybGQ="}  # "Hello World" in base64
    result = client.decode_message_body(message)
    assert result == "Hello World"

    # Test empty message
    result = client.decode_message_body({})
    assert result == ""

    # Test invalid base64
    message = {"data": "invalid-base64"}
    result = client.decode_message_body(message)
    assert result == ""
