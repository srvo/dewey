import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.email.email_triage_workflow import EmailTriageWorkflow


class TestEmailTriageWorkflow:
    """Tests for the EmailTriageWorkflow class."""

    @pytest.fixture
    def email_triage_workflow(self) -> EmailTriageWorkflow:
        """Fixture for creating an EmailTriageWorkflow instance."""
        workflow = EmailTriageWorkflow()
        workflow.logger = MagicMock()  # Mock the logger
        return workflow

    def test_init(self, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the __init__ method."""
        assert email_triage_workflow.name == "EmailTriageWorkflow"
        assert email_triage_workflow.config_section == "email_triage"
        assert email_triage_workflow.requires_db is True
        assert email_triage_workflow.enable_llm is True

    @patch("dewey.core.crm.email.email_triage_workflow.EmailTriageWorkflow.get_config_value")
    def test_run_success(self, mock_get_config_value: MagicMock, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the run method with successful execution."""
        mock_get_config_value.return_value = 50
        email_triage_workflow.db_conn = MagicMock()
        email_triage_workflow.llm_client = MagicMock()

        email_triage_workflow.run()

        email_triage_workflow.logger.info.assert_called_with("Email triage workflow completed.")
        mock_get_config_value.assert_called_with('max_emails_to_process', 100)

    @patch("dewey.core.crm.email.email_triage_workflow.EmailTriageWorkflow.get_config_value")
    def test_run_exception(self, mock_get_config_value: MagicMock, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the run method when an exception occurs."""
        mock_get_config_value.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            email_triage_workflow.run()

        email_triage_workflow.logger.error.assert_called()

    def test_execute_success(self, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the execute method with successful execution."""
        email_triage_workflow.parse_args = MagicMock()
        email_triage_workflow.run = MagicMock()
        email_triage_workflow._cleanup = MagicMock()

        email_triage_workflow.execute()

        email_triage_workflow.parse_args.assert_called_once()
        email_triage_workflow.run.assert_called_once()
        email_triage_workflow._cleanup.assert_called_once()

    def test_execute_keyboard_interrupt(self, email_triage_workflow: EmailTriageWorkflow, capsys: pytest.CaptureFixture) -> None:
        """Test the execute method when a KeyboardInterrupt occurs."""
        email_triage_workflow.parse_args = MagicMock()
        email_triage_workflow.run = MagicMock(side_effect=KeyboardInterrupt)
        email_triage_workflow._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            email_triage_workflow.execute()

        assert exc_info.value.code == 1
        email_triage_workflow.logger.warning.assert_called_with("Script interrupted by user")
        email_triage_workflow._cleanup.assert_called_once()

    def test_execute_exception(self, email_triage_workflow: EmailTriageWorkflow, capsys: pytest.CaptureFixture) -> None:
        """Test the execute method when a general exception occurs."""
        email_triage_workflow.parse_args = MagicMock()
        email_triage_workflow.run = MagicMock(side_effect=ValueError("Test error"))
        email_triage_workflow._cleanup = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            email_triage_workflow.execute()

        assert exc_info.value.code == 1
        email_triage_workflow.logger.error.assert_called()
        email_triage_workflow._cleanup.assert_called_once()

    def test_cleanup(self, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the _cleanup method."""
        email_triage_workflow.db_conn = MagicMock()
        email_triage_workflow._cleanup()
        email_triage_workflow.db_conn.close.assert_called_once()

        # Test when db_conn is None
        email_triage_workflow.db_conn = None
        email_triage_workflow._cleanup()

    def test_cleanup_exception(self, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the _cleanup method when closing the database connection raises an exception."""
        email_triage_workflow.db_conn = MagicMock()
        email_triage_workflow.db_conn.close.side_effect = Exception("Failed to close connection")
        email_triage_workflow._cleanup()
        email_triage_workflow.logger.warning.assert_called()

    def test_get_config_value(self, email_triage_workflow: EmailTriageWorkflow) -> None:
        """Test the get_config_value method."""
        email_triage_workflow.config = {"level1": {"level2": "value"}}
        assert email_triage_workflow.get_config_value("level1.level2") == "value"
        assert email_triage_workflow.get_config_value("level1.level3", "default") == "default"
        assert email_triage_workflow.get_config_value("level3", "default") == "default"

        email_triage_workflow.config = {}
        assert email_triage_workflow.get_config_value("level1", "default") == "default"
