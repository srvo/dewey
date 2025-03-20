import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.crm.email.email_prioritization import EmailPrioritization


class TestEmailPrioritization:
    """Test suite for the EmailPrioritization class."""

    @pytest.fixture
    def email_prioritization(self) -> EmailPrioritization:
        """Fixture to create an EmailPrioritization instance."""
        return EmailPrioritization()

    def test_init(self, email_prioritization: EmailPrioritization) -> None:
        """Test the __init__ method."""
        assert email_prioritization.name == "EmailPrioritization"
        assert email_prioritization.config_section == "email_prioritization"
        assert email_prioritization.logger is not None

    def test_run_success(
        self, email_prioritization: EmailPrioritization, caplog
    ) -> None:
        """Test the run method with successful execution."""
        caplog.set_level(logging.INFO)
        email_prioritization.run()
        assert "Starting email prioritization process." in caplog.text
        assert "Email prioritization process completed." in caplog.text

    def test_run_exception(
        self, email_prioritization: EmailPrioritization, caplog
    ) -> None:
        """Test the run method when an exception occurs."""
        caplog.set_level(logging.INFO)
        email_prioritization.logger.info = MagicMock(
            side_effect=Exception("Test Exception")
        )
        with pytest.raises(Exception, match="Test Exception"):
            email_prioritization.run()
        assert "Starting email prioritization process." in caplog.text
