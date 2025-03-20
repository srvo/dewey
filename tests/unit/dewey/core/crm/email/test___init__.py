import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.email import EmailProcessor


class TestEmailProcessor:
    """Tests for the EmailProcessor class."""

    @pytest.fixture
    def email_processor(self) -> EmailProcessor:
        """Fixture for creating an EmailProcessor instance."""
        return EmailProcessor()

    def test_init(self, email_processor: EmailProcessor) -> None:
        """Tests the __init__ method."""
        assert email_processor.name == "EmailProcessor"
        assert email_processor.config_section == "email_processor"
        assert email_processor.requires_db is True
        assert email_processor.enable_llm is True
        assert isinstance(email_processor, BaseScript)

    @patch("dewey.core.crm.email.EmailProcessor.get_config_value")
    @patch("dewey.core.crm.email.EmailProcessor.db_conn")
    @patch("dewey.core.crm.email.EmailProcessor.llm_client")
    def test_run(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        email_processor: EmailProcessor,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the run method."""
        mock_get_config_value.return_value = 50
        mock_db_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            "email1",
            "email2",
        ]
        caplog.set_level(logging.INFO)

        email_processor.run()

        assert "Starting email processing..." in caplog.text
        mock_get_config_value.assert_called_with("max_emails", 100)
        assert "Maximum emails to process: 50" in caplog.text
        mock_db_conn.cursor.return_value.__enter__.return_value.execute.assert_called_with(
            "SELECT * FROM emails LIMIT 10"
        )
        assert "Fetched 2 emails from the database." in caplog.text
        assert "LLM client is configured but not used in this example." in caplog.text
        assert "Email processing completed." in caplog.text

    @patch("dewey.core.crm.email.EmailProcessor.get_config_value")
    @patch("dewey.core.crm.email.EmailProcessor.db_conn")
    @patch("dewey.core.crm.email.EmailProcessor.llm_client")
    def test_run_db_error(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        email_processor: EmailProcessor,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the run method with a database error."""
        mock_get_config_value.return_value = 50
        mock_db_conn.cursor.side_effect = Exception("Database error")
        caplog.set_level(logging.ERROR)

        email_processor.run()

        assert "Starting email processing..." in caplog.text
        assert "Error fetching emails from the database: Database error" in caplog.text
        assert "Email processing completed." in caplog.text

    @patch("dewey.core.crm.email.EmailProcessor.get_config_value")
    @patch("dewey.core.crm.email.EmailProcessor.db_conn")
    @patch("dewey.core.crm.email.EmailProcessor.llm_client")
    def test_run_llm_error(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        email_processor: EmailProcessor,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the run method with an LLM error."""
        mock_get_config_value.return_value = 50
        mock_llm_client.generate_text.side_effect = Exception("LLM error")
        mock_db_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            "email1",
            "email2",
        ]
        caplog.set_level(logging.ERROR)

        email_processor.run()

        assert "Starting email processing..." in caplog.text
        assert "Error using LLM client: LLM error" in caplog.text
        assert "Email processing completed." in caplog.text

    @patch("dewey.core.crm.email.EmailProcessor.execute")
    def test_main(self, mock_execute: MagicMock) -> None:
        """Tests the main execution block."""
        with patch("dewey.core.crm.email.__name__", "__main__"):
            from dewey.core.crm.email import EmailProcessor

            EmailProcessor().execute()
            mock_execute.assert_called_once()
