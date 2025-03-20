import logging
from unittest.mock import patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.gmail.view_email import ViewEmail


class TestViewEmail:
    """Test suite for the ViewEmail class."""

    @pytest.fixture
    def view_email(self) -> ViewEmail:
        """Fixture to create a ViewEmail instance."""
        return ViewEmail()

    def test_view_email_initialization(self, view_email: ViewEmail) -> None:
        """Test that ViewEmail is initialized correctly."""
        assert isinstance(view_email, ViewEmail)
        assert isinstance(view_email, BaseScript)
        assert view_email.config_section == "gmail"

    @patch("dewey.core.crm.gmail.view_email.ViewEmail.logger")
    def test_run_method_logs_info(
        self, mock_logger: logging.Logger, view_email: ViewEmail
    ) -> None:
        """Test that the run method logs an info message."""
        view_email.run()
        mock_logger.info.assert_called_once_with("Running ViewEmail script")

    @patch("dewey.core.crm.gmail.view_email.ViewEmail.logger")
    def test_run_method_no_errors(
        self, mock_logger: logging.Logger, view_email: ViewEmail
    ) -> None:
        """Test that the run method executes without errors."""
        try:
            view_email.run()
        except Exception as e:
            pytest.fail(f"run() raised an exception: {e}")
