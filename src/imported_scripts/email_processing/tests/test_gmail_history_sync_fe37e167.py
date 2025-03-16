"""Test Gmail history sync functionality."""

from unittest.mock import MagicMock, patch

import pytest
from database.models import EventLog
from email_processing.gmail_history_sync import (
    sync_gmail_history,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("email_processing.gmail_history_sync.redis_client") as mock:
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = True
        yield mock


@pytest.fixture
def mock_sentry():
    """Mock Sentry SDK."""
    with patch("sentry_sdk.configure_scope") as mock:
        mock.return_value.__enter__.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_process_history():
    """Mock process_history_item function."""
    with patch("email_processing.gmail_history_sync.process_history_item") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service with history API responses."""
    mock_service = MagicMock()

    # Mock users().history().list() chain
    mock_history = MagicMock()
    mock_history.list.return_value = MagicMock()
    mock_history.list.return_value.execute.return_value = {
        "history": [
            {
                "id": "2000",
                "messages": [{"id": "msg1"}],
                "messagesAdded": [
                    {
                        "message": {
                            "id": "msg1",
                            "threadId": "thread1",
                            "labelIds": ["INBOX", "UNREAD"],
                        },
                    },
                ],
            },
        ],
    }

    # Explicitly set list_next to return None to stop pagination
    mock_history.list_next = MagicMock(return_value=None)

    mock_service.users.return_value.history.return_value = mock_history
    mock_service.users.return_value.getProfile.return_value.execute.return_value = {
        "historyId": "1000",
    }

    return mock_service


@pytest.fixture
def mock_execute_gmail_api():
    """Mock the _execute_gmail_api function."""
    with patch("email_processing.gmail_history_sync._execute_gmail_api") as mock:

        def side_effect(request):
            if hasattr(request, "execute"):
                return request.execute()
            return request

        mock.side_effect = side_effect
        yield mock


@pytest.fixture
def mock_email_exists():
    """Mock Email.objects.exists()."""
    with patch("database.models.Email.objects.exists") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_full_sync():
    """Mock full_sync_gmail function."""
    with patch("email_processing.gmail_history_sync.full_sync_gmail") as mock:
        mock.return_value = (True, 1)
        yield mock


@pytest.mark.django_db
class TestGmailHistorySync:
    @patch("email_processing.gmail_history_sync.get_gmail_service")
    def test_sync_from_history_id(
        self,
        mock_get_service,
        mock_gmail_service,
        mock_execute_gmail_api,
        mock_redis,
        mock_sentry,
        mock_process_history,
        mock_email_exists,
    ) -> None:
        """Test syncing changes from a given history ID."""
        # Setup
        mock_get_service.return_value = mock_gmail_service
        start_history_id = "1000"

        # Execute
        success, messages_updated, pages = sync_gmail_history(start_history_id)

        # Verify
        assert success is True
        assert messages_updated == 1
        assert pages == 1

        # Verify the history API was called with correct parameters
        mock_gmail_service.users().history().list.assert_called_once_with(
            userId="me",
            startHistoryId=start_history_id,
        )

        # Verify process_history_item was called
        mock_process_history.assert_called_once()

    @patch("email_processing.gmail_history_sync.get_gmail_service")
    def test_full_sync_when_no_emails(
        self,
        mock_get_service,
        mock_gmail_service,
        mock_execute_gmail_api,
        mock_redis,
        mock_sentry,
        mock_process_history,
        mock_email_exists,
        mock_full_sync,
    ) -> None:
        """Test that a full sync is performed when no emails exist."""
        # Setup
        mock_get_service.return_value = mock_gmail_service
        mock_email_exists.return_value = False

        # Execute
        success, messages_updated, pages = sync_gmail_history()

        # Verify
        assert success is True
        assert messages_updated == 1
        assert pages == 1

        # Verify full sync was called
        mock_full_sync.assert_called_once()

    @patch("email_processing.gmail_history_sync.get_gmail_service")
    def test_error_handling(
        self,
        mock_get_service,
        mock_gmail_service,
        mock_execute_gmail_api,
        mock_redis,
        mock_sentry,
        mock_process_history,
        mock_email_exists,
    ) -> None:
        """Test handling of API errors during sync."""
        # Setup
        mock_get_service.return_value = mock_gmail_service
        mock_execute_gmail_api.side_effect = Exception("API Error")

        # Execute
        success, messages_updated, pages = sync_gmail_history("1000")

        # Verify
        assert success is False
        assert messages_updated == 0
        assert pages == 0

        # Verify error was logged (get first error log)
        error_log = EventLog.objects.filter(event_type="SYNC_ERROR").first()
        assert error_log is not None
        assert "API Error" in error_log.details["error_message"]
