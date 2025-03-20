import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.yahoo_finance_engine import YahooFinanceEngine


class TestYahooFinanceEngine:
    """Tests for the YahooFinanceEngine class."""

    @pytest.fixture
    def yahoo_finance_engine(self) -> YahooFinanceEngine:
        """Fixture for creating a YahooFinanceEngine instance."""
        return YahooFinanceEngine()

    @patch(
        "dewey.core.engines.yahoo_finance_engine.YahooFinanceEngine.get_config_value"
    )
    def test_run_success(
        self,
        mock_get_config_value: pytest.fixture,
        yahoo_finance_engine: YahooFinanceEngine,
    ) -> None:
        """Tests the run method with a valid API key."""
        mock_get_config_value.return_value = "test_api_key"
        with patch.object(yahoo_finance_engine.logger, "info") as mock_logger_info:
            yahoo_finance_engine.run()
            assert mock_logger_info.call_count == 2
            mock_get_config_value.assert_called_once_with("api_key")

    @patch(
        "dewey.core.engines.yahoo_finance_engine.YahooFinanceEngine.get_config_value"
    )
    def test_run_no_api_key(
        self,
        mock_get_config_value: pytest.fixture,
        yahoo_finance_engine: YahooFinanceEngine,
    ) -> None:
        """Tests the run method when the API key is not found in the configuration."""
        mock_get_config_value.return_value = None
        with patch.object(yahoo_finance_engine.logger, "error") as mock_logger_error:
            yahoo_finance_engine.run()
            mock_logger_error.assert_called_once_with(
                "API key not found in configuration."
            )
            mock_get_config_value.assert_called_once_with("api_key")

    def test_init(self, yahoo_finance_engine: YahooFinanceEngine) -> None:
        """Tests the __init__ method to ensure proper initialization."""
        assert yahoo_finance_engine.config_section == "yahoo_finance"
        assert isinstance(yahoo_finance_engine.logger, logging.Logger)
