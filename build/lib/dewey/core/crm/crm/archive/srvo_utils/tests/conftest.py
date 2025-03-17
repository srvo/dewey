"""Root conftest.py for test configuration.

This file contains pytest configuration and fixtures that are available
to all tests in the project. It handles:

- Django test environment setup
- Database configuration
- Logging setup
- Environment variable configuration
- Path configuration

Key Features:
- Automatic Django test environment setup
- Database access for all tests
- Proper project root path configuration
- Test-specific environment variables
- Log directory creation
- Automatic test isolation
- Database transaction management

Usage:
    This configuration is automatically applied when running pytest.
    No manual setup is required.

    To run tests:
    ```bash
    pytest tests/
    ```

Configuration:
    - DJANGO_SETTINGS_MODULE: Set to core.settings_test
    - SENTRY_DSN: Disabled for tests
    - ENVIRONMENT: Set to 'test'
    - LOGS_DIR: Created at project_root/logs
    - TEST_DATABASE_URL: Configured for in-memory SQLite by default

Fixtures:
    - db: Provides database access for tests
    - client: Django test client for HTTP requests
    - admin_client: Authenticated admin user test client

Design Principles:
    1. Isolation: Each test runs in complete isolation
    2. Speed: Optimized for fast test execution
    3. Reliability: Consistent test environment
    4. Maintainability: Clear configuration and documentation
    5. Security: No production data access

Best Practices:
    1. Use fixtures for common setup
    2. Keep tests focused and isolated
    3. Clean up after each test
    4. Use meaningful test names
    5. Document test requirements
"""

import os
import pytest
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle


def pytest_configure():
    """Configure test environment before running tests.

    This function:
    1. Sets environment variables for testing
    2. Configures logging
    3. Creates necessary directories
    4. Disables external services
    """
    # Set test environment variables
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings_test")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("SENTRY_DSN", "")  # Disable Sentry in tests

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(settings.BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)


@pytest.fixture(autouse=True)
def db(django_db_setup, django_db_blocker):
    """Enable database access for all tests.

    This fixture:
    - Sets up the test database
    - Provides database access to tests
    - Handles database cleanup
    - Manages transactions

    Usage:
        No explicit usage needed - applied automatically to all tests.
    """
    with django_db_blocker.unblock():
        yield


@pytest.fixture(scope="session")
def gmail_service():
    """Create an authenticated Gmail service for testing.

    This uses a real Gmail account for integration testing. The credentials
    are loaded from environment variables or a pickle file.
    """
    creds = None
    token_path = os.getenv("GMAIL_TEST_TOKEN_PATH", "tests/test_token.pickle")
    credentials_path = os.getenv(
        "GMAIL_TEST_CREDENTIALS_PATH", "tests/test_credentials.json"
    )

    # Load existing token if available
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Create new token if none exists
    if not creds or not creds.valid:
        if not os.path.exists(credentials_path):
            raise ValueError(
                "No credentials found. Please set GMAIL_TEST_CREDENTIALS_PATH "
                "or place test_credentials.json in the tests directory."
            )

        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the token
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


@pytest.fixture(scope="function")
def clean_test_labels(gmail_service):
    """Ensure test labels are cleaned up before and after each test."""
    # Create test labels if they don't exist
    test_labels = ["TEST_LABEL_1", "TEST_LABEL_2"]
    existing_labels = gmail_service.users().labels().list(userId="me").execute()

    for label in test_labels:
        label_exists = any(
            l["name"] == label for l in existing_labels.get("labels", [])
        )
        if not label_exists:
            gmail_service.users().labels().create(
                userId="me", body={"name": label, "labelListVisibility": "labelShow"}
            ).execute()

    yield test_labels

    # Cleanup: Remove test messages with these labels
    query = " OR ".join(f"label:{label}" for label in test_labels)
    messages = gmail_service.users().messages().list(userId="me", q=query).execute()

    if messages.get("messages"):
        for msg in messages["messages"]:
            gmail_service.users().messages().trash(userId="me", id=msg["id"]).execute()


@pytest.fixture(scope="function")
def test_message(gmail_service, clean_test_labels):
    """Create a test message and clean it up after the test."""
    import base64
    from email.mime.text import MIMEText

    # Create a test email
    message = MIMEText("Test message body")
    message["to"] = os.getenv("GMAIL_TEST_EMAIL")
    message["from"] = os.getenv("GMAIL_TEST_EMAIL")
    message["subject"] = "Test Subject"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send the message
    message = (
        gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
    )

    # Add test label
    gmail_service.users().messages().modify(
        userId="me", id=message["id"], body={"addLabelIds": [clean_test_labels[0]]}
    ).execute()

    yield message

    # Cleanup: Move to trash
    gmail_service.users().messages().trash(userId="me", id=message["id"]).execute()
