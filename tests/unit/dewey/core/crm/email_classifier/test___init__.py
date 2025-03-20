import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.crm.email_classifier import EmailClassifier
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class TestEmailClassifier:
    """Tests for the EmailClassifier class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        with patch("dewey.core.crm.email_classifier.BaseScript", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def mock_database_connection(self) -> MagicMock:
        """Mocks the DatabaseConnection class."""
        with patch(
            "dewey.core.crm.email_classifier.DatabaseConnection", autospec=True
        ) as mock:
            yield mock

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Mocks the LLMClient class."""
        with patch("dewey.core.crm.email_classifier.LLMClient", autospec=True) as mock:
            yield mock

    def test_init_no_args(self, mock_base_script: MagicMock) -> None:
        """Tests the __init__ method with no arguments."""
        classifier = EmailClassifier()
        mock_base_script.assert_called_once_with(
            config_section=None, requires_db=False, enable_llm=False
        )
        assert classifier.name == "EmailClassifier"
        assert classifier.description is None
        assert classifier.config_section is None
        assert classifier.requires_db is False
        assert classifier.enable_llm is False

    def test_init_with_args(self, mock_base_script: MagicMock) -> None:
        """Tests the __init__ method with arguments."""
        classifier = EmailClassifier(
            config_section="test_section",
            requires_db=True,
            enable_llm=True,
            name="TestClassifier",
            description="Test Description",
        )
        mock_base_script.assert_called_once_with(
            config_section="test_section", requires_db=True, enable_llm=True, name="TestClassifier", description="Test Description"
        )
        assert classifier.name == "TestClassifier"
        assert classifier.description == "Test Description"
        assert classifier.config_section == "test_section"
        assert classifier.requires_db is True
        assert classifier.enable_llm is True

    def test_run_success(self) -> None:
        """Tests the run method with successful execution."""
        with patch.object(EmailClassifier, "get_config_value") as mock_get_config_value:
            mock_get_config_value.return_value = "test_api_key"
            with patch.object(EmailClassifier, "logger") as mock_logger:
                classifier = EmailClassifier()
                classifier.run()

                mock_logger.info.assert_called_with(
                    "Email classification process completed."
                )
                mock_get_config_value.assert_called_once_with("email_classifier.api_key")
                mock_logger.debug.assert_called_with(
                    "Retrieved API key: test_api_key"
                )

    def test_run_config_error(self) -> None:
        """Tests the run method when there's an error retrieving the API key."""
        with patch.object(EmailClassifier, "get_config_value") as mock_get_config_value:
            mock_get_config_value.side_effect = KeyError("api_key")
            with patch.object(EmailClassifier, "logger") as mock_logger:
                classifier = EmailClassifier()
                with pytest.raises(KeyError):
                    classifier.run()
                mock_logger.info.assert_called_once_with(
                    "Starting email classification process."
                )
                mock_get_config_value.assert_called_once_with("email_classifier.api_key")
                mock_logger.error.assert_not_called()

    def test_run_no_api_key(self) -> None:
        """Tests the run method when the API key is not found in the config."""
        with patch.object(EmailClassifier, "get_config_value") as mock_get_config_value:
            mock_get_config_value.return_value = None
            with patch.object(EmailClassifier, "logger") as mock_logger:
                classifier = EmailClassifier()
                classifier.run()

                mock_logger.info.assert_called_with(
                    "Email classification process completed."
                )
                mock_get_config_value.assert_called_once_with("email_classifier.api_key")
                mock_logger.debug.assert_called_with("Retrieved API key: None")
