import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.duckduckgo_engine import DuckDuckGoEngine


class TestDuckDuckGoEngine:
    """Unit tests for the DuckDuckGoEngine class."""

    @pytest.fixture
    def duckduckgo_engine(self) -> DuckDuckGoEngine:
        """Fixture to create a DuckDuckGoEngine instance."""
        return DuckDuckGoEngine()

    def test_init(self, duckduckgo_engine: DuckDuckGoEngine) -> None:
        """Test the __init__ method."""
        assert duckduckgo_engine.name == "DuckDuckGoEngine"
        assert duckduckgo_engine.config_section == "engines.duckduckgo_engine"
        assert duckduckgo_engine.logger is not None
        assert isinstance(duckduckgo_engine.logger, logging.Logger)

    @patch("dewey.core.engines.duckduckgo_engine.DuckDuckGoEngine.logger")
    def test_run(self, mock_logger, duckduckgo_engine: DuckDuckGoEngine) -> None:
        """Test the run method."""
        duckduckgo_engine.run()
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Running DuckDuckGo engine...")
        mock_logger.info.assert_any_call("DuckDuckGo engine execution completed.")
