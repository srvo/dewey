import pytest
from unittest.mock import MagicMock
from dewey.core.crm.email.email_data_generator import EmailDataGenerator
import logging
from dewey.core.base_script import BaseScript  # Import BaseScript


class TestEmailDataGenerator:
    """Tests for the EmailDataGenerator class."""

    @pytest.fixture
    def email_data_generator(self):
        """Fixture for creating an EmailDataGenerator instance with mocked dependencies."""
        generator = EmailDataGenerator()
        generator.logger = MagicMock(spec=logging.Logger)
        generator.db_conn = MagicMock()
        generator.llm_client = MagicMock()
        return generator

    def test_init(self, email_data_generator):
        """Test the __init__ method."""
        assert email_data_generator.config_section == "email_data_generator"
        assert email_data_generator.requires_db is True
        assert email_data_generator.enable_llm is True
        assert isinstance(email_data_generator, BaseScript)

    def test_run_success(self, email_data_generator):
        """Test the run method with successful database and LLM calls."""
        # Mock configuration values
        email_data_generator.get_config_value = MagicMock(return_value=5)

        # Mock database interaction
        cursor_mock = MagicMock()
        email_data_generator.db_conn.cursor.return_value.__enter__.return_value = (
            cursor_mock
        )
        cursor_mock.fetchone.return_value = [1]

        # Mock LLM response
        email_data_generator.llm_client.generate_text.return_value = (
            "Test email subject"
        )

        # Run the method
        email_data_generator.run()

        # Assertions
        email_data_generator.get_config_value.assert_called_with("num_emails", 10)
        email_data_generator.logger.info.assert_any_call(
            "Starting email data generation..."
        )
        email_data_generator.logger.info.assert_any_call("Generating 5 emails.")
        cursor_mock.execute.assert_called_with("SELECT 1")
        email_data_generator.logger.info.assert_any_call(
            "Database connection test: [1]"
        )
        email_data_generator.llm_client.generate_text.assert_called_with(
            "Write a short email subject."
        )
        email_data_generator.logger.info.assert_any_call(
            "LLM response: Test email subject"
        )
        email_data_generator.logger.info.assert_any_call(
            "Email data generation completed."
        )

    def test_run_db_error(self, email_data_generator):
        """Test the run method with a database connection error."""
        # Mock configuration values
        email_data_generator.get_config_value = MagicMock(return_value=5)

        # Mock database connection error
        email_data_generator.db_conn.cursor.side_effect = Exception("Database error")

        # Run the method
        email_data_generator.run()

        # Assertions
        email_data_generator.logger.info.assert_any_call(
            "Starting email data generation..."
        )
        email_data_generator.logger.info.assert_any_call("Generating 5 emails.")
        email_data_generator.logger.error.assert_called_with(
            "Error connecting to database: Database error"
        )
        email_data_generator.logger.info.assert_any_call(
            "Email data generation completed."
        )

    def test_run_llm_error(self, email_data_generator):
        """Test the run method with an LLM error."""
        # Mock configuration values
        email_data_generator.get_config_value = MagicMock(return_value=5)

        # Mock database interaction
        cursor_mock = MagicMock()
        email_data_generator.db_conn.cursor.return_value.__enter__.return_value = (
            cursor_mock
        )
        cursor_mock.fetchone.return_value = [1]

        # Mock LLM error
        email_data_generator.llm_client.generate_text.side_effect = Exception(
            "LLM error"
        )

        # Run the method
        email_data_generator.run()

        # Assertions
        email_data_generator.logger.info.assert_any_call(
            "Starting email data generation..."
        )
        email_data_generator.logger.info.assert_any_call("Generating 5 emails.")
        cursor_mock.execute.assert_called_with("SELECT 1")
        email_data_generator.logger.info.assert_any_call(
            "Database connection test: [1]"
        )
        email_data_generator.logger.error.assert_called_with(
            "Error using LLM: LLM error"
        )
        email_data_generator.logger.info.assert_any_call(
            "Email data generation completed."
        )

    def test_run_no_emails_configured(self, email_data_generator):
        """Test the run method when no 'num_emails' is configured."""
        # Mock configuration values to return None, triggering the default value
        email_data_generator.get_config_value = MagicMock(return_value=None)

        # Mock database interaction
        cursor_mock = MagicMock()
        email_data_generator.db_conn.cursor.return_value.__enter__.return_value = (
            cursor_mock
        )
        cursor_mock.fetchone.return_value = [1]

        # Mock LLM response
        email_data_generator.llm_client.generate_text.return_value = (
            "Test email subject"
        )

        # Run the method
        email_data_generator.run()

        # Assertions
        email_data_generator.get_config_value.assert_called_with("num_emails", 10)
        email_data_generator.logger.info.assert_any_call(
            "Starting email data generation..."
        )
        email_data_generator.logger.info.assert_any_call(
            "Generating 10 emails."
        )  # Verify default value is used
        cursor_mock.execute.assert_called_with("SELECT 1")
        email_data_generator.logger.info.assert_any_call(
            "Database connection test: [1]"
        )
        email_data_generator.llm_client.generate_text.assert_called_with(
            "Write a short email subject."
        )
        email_data_generator.logger.info.assert_any_call(
            "LLM response: Test email subject"
        )
        email_data_generator.logger.info.assert_any_call(
            "Email data generation completed."
        )
