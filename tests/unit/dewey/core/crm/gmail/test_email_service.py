import datetime
import logging
import signal
import time
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.gmail.email_service import EmailService


class TestEmailService:
    """Unit tests for the EmailService class."""

    @pytest.fixture
    def mock_gmail_client(self) -> MagicMock:
        """Fixture for a mock GmailClient."""
        return MagicMock()

    @pytest.fixture
    def mock_email_processor(self) -> MagicMock:
        """Fixture for a mock EmailProcessor."""
        return MagicMock()

    @pytest.fixture
    def email_service(self, mock_gmail_client: MagicMock, mock_email_processor: MagicMock) -> EmailService:
        """Fixture for an EmailService instance with mocked dependencies."""
        with patch("dewey.core.crm.gmail.email_service.BaseScript.__init__", return_value=None):
            service = EmailService(gmail_client=mock_gmail_client, email_processor=mock_email_processor)
            service.logger = MagicMock()  # Mock the logger
            service.get_config_value = MagicMock(side_effect=lambda key, default: default)  # Mock config
            return service

    def test_init(self, mock_gmail_client: MagicMock, mock_email_processor: MagicMock) -> None:
        """Test the initialization of the EmailService."""
        with patch("dewey.core.crm.gmail.email_service.BaseScript.__init__", return_value=None):
            service = EmailService(gmail_client=mock_gmail_client, email_processor=mock_email_processor)
            assert service.gmail_client == mock_gmail_client
            assert service.email_processor == mock_email_processor
            assert service.running is False
            assert service.last_run is None

    def test_setup_signal_handlers(self, email_service: EmailService) -> None:
        """Test the _setup_signal_handlers method."""
        with patch("signal.signal") as mock_signal:
            email_service._setup_signal_handlers()
            mock_signal.assert_called()
            assert mock_signal.call_count == 2

    def test_handle_signal(self, email_service: EmailService) -> None:
        """Test the handle_signal method."""
        email_service.handle_signal(signal.SIGINT, None)
        assert email_service.running is False
        email_service.logger.warning.assert_called()

    def test_fetch_cycle_success(self, email_service: EmailService, mock_gmail_client: MagicMock,
                                 mock_email_processor: MagicMock) -> None:
        """Test a successful fetch cycle."""
        mock_gmail_client.fetch_emails.return_value = {'messages': [{'id': '123'}]}
        mock_gmail_client.get_message.return_value = {'id': '123', 'payload': 'test'}
        mock_email_processor.process_email.return_value = True

        email_service.fetch_cycle()

        mock_gmail_client.fetch_emails.assert_called_once()
        mock_gmail_client.get_message.assert_called_with('123')
        mock_email_processor.process_email.assert_called_with({'id': '123', 'payload': 'test'})
        email_service.logger.info.assert_called()
        assert email_service.last_run is not None

    def test_fetch_cycle_no_emails(self, email_service: EmailService, mock_gmail_client: MagicMock) -> None:
        """Test fetch cycle when no emails are returned."""
        mock_gmail_client.fetch_emails.return_value = {'messages': []}

        email_service.fetch_cycle()

        mock_gmail_client.fetch_emails.assert_called_once()
        email_service.logger.info.assert_called_with("No emails to fetch")
        assert email_service.last_run is not None

    def test_fetch_cycle_get_message_failure(self, email_service: EmailService, mock_gmail_client: MagicMock) -> None:
        """Test fetch cycle when getting a message fails."""
        mock_gmail_client.fetch_emails.return_value = {'messages': [{'id': '123'}]}
        mock_gmail_client.get_message.return_value = None

        email_service.fetch_cycle()

        mock_gmail_client.get_message.assert_called_with('123')
        email_service.logger.warning.assert_called_with("Could not retrieve email 123")
        assert email_service.last_run is not None

    def test_fetch_cycle_process_email_failure(self, email_service: EmailService, mock_gmail_client: MagicMock,
                                               mock_email_processor: MagicMock) -> None:
        """Test fetch cycle when processing an email fails."""
        mock_gmail_client.fetch_emails.return_value = {'messages': [{'id': '123'}]}
        mock_gmail_client.get_message.return_value = {'id': '123', 'payload': 'test'}
        mock_email_processor.process_email.return_value = False

        email_service.fetch_cycle()

        mock_email_processor.process_email.assert_called_with({'id': '123', 'payload': 'test'})
        email_service.logger.warning.assert_called_with("Failed to fully process email 123")
        assert email_service.last_run is not None

    def test_fetch_cycle_exception(self, email_service: EmailService, mock_gmail_client: MagicMock) -> None:
        """Test fetch cycle when an exception occurs."""
        mock_gmail_client.fetch_emails.side_effect = Exception("Test Exception")

        email_service.fetch_cycle()

        email_service.logger.error.assert_called()
        assert email_service.last_run is None

    def test_run_success(self, email_service: EmailService) -> None:
        """Test the run method."""
        email_service.running = True
        email_service.last_run = None
        email_service.fetch_cycle = MagicMock()
        email_service.check_interval = 0.01  # Shorten check interval for testing
        email_service.fetch_interval = 0.02

        with patch("time.sleep", side_effect=lambda x: email_service.handle_signal(signal.SIGINT, None)):
            email_service.run()

        assert email_service.running is False
        email_service.fetch_cycle.assert_called()
        email_service.logger.info.assert_called()

    def test_run_already_running(self, email_service: EmailService) -> None:
        """Test the run method when already running."""
        email_service.running = True
        email_service.last_run = datetime.datetime.now()
        email_service.fetch_cycle = MagicMock()
        email_service.check_interval = 0.01  # Shorten check interval for testing
        email_service.fetch_interval = 0.02

        with patch("time.sleep", side_effect=lambda x: email_service.handle_signal(signal.SIGINT, None)):
            email_service.run()

        assert email_service.running is False
        email_service.fetch_cycle.assert_called()
        email_service.logger.info.assert_called()

    def test_run_exception(self, email_service: EmailService) -> None:
        """Test the run method when an exception occurs."""
        email_service.running = True
        email_service.fetch_cycle = MagicMock(side_effect=Exception("Test Exception"))
        email_service.check_interval = 0.01  # Shorten check interval for testing

        with patch("time.sleep", side_effect=lambda x: email_service.handle_signal(signal.SIGINT, None)):
            email_service.run()

        assert email_service.running is False
        email_service.logger.error.assert_called()
        email_service.logger.info.assert_called()

    def test_run_keyboard_interrupt(self, email_service: EmailService) -> None:
        """Test the run method when a KeyboardInterrupt occurs."""
        email_service.running = True
        email_service.fetch_cycle = MagicMock(side_effect=KeyboardInterrupt)
        email_service.check_interval = 0.01  # Shorten check interval for testing

        with pytest.raises(KeyboardInterrupt):
            email_service.run()

        assert email_service.running is True  # Should still be true when KeyboardInterrupt is raised
        email_service.logger.info.assert_called()
