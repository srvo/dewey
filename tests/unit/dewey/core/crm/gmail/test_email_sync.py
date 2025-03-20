import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.gmail.email_sync import EmailSync


class TestEmailSync:
    """Unit tests for the EmailSync class."""

    @pytest.fixture
    def email_sync(self) -> EmailSync:
        """Fixture to create an EmailSync instance with mocked dependencies."""
        with patch("dewey.core.crm.gmail.email_sync.BaseScript.__init__", return_value=None):
            email_sync = EmailSync()
            email_sync.logger = MagicMock(spec=logging.Logger)
            email_sync.get_config_value = MagicMock()
            return email_sync

    def test_init(self) -> None:
        """Test the __init__ method of EmailSync."""
        with patch("dewey.core.crm.gmail.email_sync.BaseScript.__init__") as mock_init:
            EmailSync(config_section="test_section", arg1="value1", kwarg1="value2")
            mock_init.assert_called_once_with(config_section="test_section", arg1="value1", kwarg1="value2")

    def test_run_api_key_found(self, email_sync: EmailSync) -> None:
        """Test the run method when the Gmail API key is found in the configuration."""
        email_sync.get_config_value.return_value = "test_api_key"
        email_sync.run()

        email_sync.logger.info.assert_called_with("Email synchronization completed.")
        email_sync.logger.debug.assert_called_with("Gmail API key found in configuration.")
        assert email_sync.logger.warning.call_count == 0

    def test_run_api_key_not_found(self, email_sync: EmailSync) -> None:
        """Test the run method when the Gmail API key is not found in the configuration."""
        email_sync.get_config_value.return_value = None
        email_sync.run()

        email_sync.logger.info.assert_called_with("Email synchronization completed.")
        email_sync.logger.warning.assert_called_with("Gmail API key not found in configuration.")
        assert email_sync.logger.debug.call_count == 0

    def test_run_exception_handling(self, email_sync: EmailSync) -> None:
        """Test the run method handles exceptions gracefully."""
        email_sync.get_config_value.side_effect = Exception("Config error")

        with pytest.raises(Exception, match="Config error"):
            email_sync.run()

        email_sync.logger.error.assert_called()
