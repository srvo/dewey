import pytest
from unittest.mock import patch
from django.test import Client
from django.contrib.auth import get_user_model
from core.api import api


@pytest.fixture(scope="session", autouse=True)
def ninja_api():
    """Ensure we only have one Django Ninja API instance during testing."""
    return api


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user():
    User = get_user_model()
    return User.objects.create_user(email="test@example.com", password="testpass123")


@pytest.fixture
def admin_user():
    User = get_user_model()
    return User.objects.create_superuser(
        email="admin@example.com", password="testpass123"
    )


@pytest.fixture
def mock_gmail_fixture():
    with patch("email_processing.gmail_client.GmailClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.authenticate.return_value = None
        mock_instance.fetch_emails.return_value = []
        mock_instance.parse_email.return_value = {
            "subject": "Test Email",
            "body": "Test Body",
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "date": "2025-01-16T00:00:00Z",
        }
        yield mock_instance


@pytest.fixture
def mock_service_fixture(mock_gmail_fixture):
    with patch("email_processing.service.EmailProcessingService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.gmail_client = mock_gmail_fixture
        mock_instance.process_new_emails.return_value = []
        mock_instance.process_single_email.return_value = None
        mock_instance.process_contacts.return_value = None
        yield mock_instance
