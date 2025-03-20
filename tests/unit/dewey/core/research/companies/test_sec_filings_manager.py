tests/unit/dewey/core/research/companies/test_sec_filings_manager.py
import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.research.companies.sec_filings_manager import SecFilingsManager


class TestSecFilingsManager:
    """Unit tests for the SecFilingsManager class."""

    @pytest.fixture
    def sec_filings_manager(self) -> SecFilingsManager:
        """Fixture to create a SecFilingsManager instance."""
        with patch("dewey.core.base_script.BaseScript.__init__", return_value=None):
            manager = SecFilingsManager()
        manager.logger = logging.getLogger(__name__)  # type: ignore
        return manager

    def test_init(self, sec_filings_manager: SecFilingsManager) -> None:
        """Test the __init__ method."""
        assert sec_filings_manager.name == "SecFilingsManager"
        assert sec_filings_manager.description is None
        assert sec_filings_manager.config is None
        assert sec_filings_manager.db_conn is None
        assert sec_filings_manager.llm_client is None

    @patch("dewey.core.research.companies.sec_filings_manager.SecFilingsManager.get_config_value")
    def test_run(self, mock_get_config_value: Any, sec_filings_manager: SecFilingsManager) -> None:
        """Test the run method."""
        mock_get_config_value.return_value = "test_value"

        sec_filings_manager.run()

        assert mock_get_config_value.call_count == 1
        mock_get_config_value.assert_called_with("example_config")
