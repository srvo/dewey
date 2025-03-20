import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.engines.consolidated_gmail_api import ConsolidatedGmailApi


class TestConsolidatedGmailApi:
    """Tests for the ConsolidatedGmailApi class."""

    @pytest.fixture
    def consolidated_gmail_api(self) -> ConsolidatedGmailApi:
        """Fixture to create an instance of ConsolidatedGmailApi."""
        return ConsolidatedGmailApi()

    def test_init(self, consolidated_gmail_api: ConsolidatedGmailApi) -> None:
        """Test the __init__ method."""
        assert consolidated_gmail_api.config_section == "consolidated_gmail_api"
        assert consolidated_gmail_api.logger is not None
        assert isinstance(consolidated_gmail_api.logger, logging.Logger)

    @patch(
        "dewey.core.engines.consolidated_gmail_api.ConsolidatedGmailApi.get_config_value"
    )
    def test_run_api_key_present(
        self,
        mock_get_config_value: MagicMock,
        consolidated_gmail_api: ConsolidatedGmailApi,
    ) -> None:
        """Test the run method when the API key is present in the config."""
        mock_get_config_value.return_value = "test_api_key"
        consolidated_gmail_api.logger = MagicMock()  # Mock the logger
        consolidated_gmail_api.run()
        mock_get_config_value.assert_called_once_with("api_key")
        consolidated_gmail_api.logger.info.assert_called_with(
            "Consolidated Gmail API script finished"
        )
        consolidated_gmail_api.logger.debug.assert_called_with(
            "API key loaded from config"
        )

    @patch(
        "dewey.core.engines.consolidated_gmail_api.ConsolidatedGmailApi.get_config_value"
    )
    def test_run_api_key_absent(
        self,
        mock_get_config_value: MagicMock,
        consolidated_gmail_api: ConsolidatedGmailApi,
    ) -> None:
        """Test the run method when the API key is absent from the config."""
        mock_get_config_value.return_value = None
        consolidated_gmail_api.logger = MagicMock()  # Mock the logger
        consolidated_gmail_api.run()
        mock_get_config_value.assert_called_once_with("api_key")
        consolidated_gmail_api.logger.info.assert_called_with(
            "Consolidated Gmail API script finished"
        )
        consolidated_gmail_api.logger.warning.assert_called_with(
            "API key not found in config"
        )

    def test_run_script_logic(
        self, consolidated_gmail_api: ConsolidatedGmailApi
    ) -> None:
        """Test the run method with some dummy script logic."""
        consolidated_gmail_api.logger = MagicMock()
        consolidated_gmail_api.get_config_value = MagicMock(return_value="dummy_value")

        # Patch any external calls that would be made within the run method
        with patch("dewey.core.engines.consolidated_gmail_api.print") as mock_print:
            consolidated_gmail_api.run()

        # Assert that the logger info was called at least twice (start and finish)
        assert consolidated_gmail_api.logger.info.call_count >= 2
        consolidated_gmail_api.logger.info.assert_called_with(
            "Consolidated Gmail API script finished"
        )
        mock_print.assert_not_called()  # Ensure no print statements are used
