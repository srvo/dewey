import logging
from unittest.mock import patch

import pytest

from dewey.core.crm.enrichment.run_enrichment import RunEnrichment


class TestRunEnrichment:
    """Unit tests for the RunEnrichment class."""

    @pytest.fixture
    def run_enrichment(self) -> RunEnrichment:
        """Fixture to create a RunEnrichment instance."""
        return RunEnrichment()

    def test_init(self, run_enrichment: RunEnrichment) -> None:
        """Test the __init__ method."""
        assert run_enrichment.name == "RunEnrichment"
        assert run_enrichment.description == "Runs enrichment tasks."
        assert run_enrichment.config_section == "enrichment"
        assert run_enrichment.logger.name == "RunEnrichment"

    @patch("dewey.core.crm.enrichment.run_enrichment.RunEnrichment.get_config_value")
    def test_run_api_key_found(
        self, mock_get_config_value: pytest.fixture, run_enrichment: RunEnrichment, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method when the API key is found in the configuration."""
        mock_get_config_value.return_value = "test_api_key"
        caplog.set_level(logging.INFO)

        run_enrichment.run()

        assert "Starting enrichment process..." in caplog.text
        assert "API key found in configuration." in caplog.text
        assert "Enrichment process completed." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.crm.enrichment.run_enrichment.RunEnrichment.get_config_value")
    def test_run_api_key_not_found(
        self, mock_get_config_value: pytest.fixture, run_enrichment: RunEnrichment, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method when the API key is not found in the configuration."""
        mock_get_config_value.return_value = None
        caplog.set_level(logging.WARNING)

        run_enrichment.run()

        assert "Starting enrichment process..." in caplog.text
        assert "API key not found in configuration. Enrichment tasks will not be executed." in caplog.text
        assert "Enrichment process completed." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")

    @patch("dewey.core.crm.enrichment.run_enrichment.RunEnrichment.get_config_value")
    def test_run_exception_handling(
        self, mock_get_config_value: pytest.fixture, run_enrichment: RunEnrichment, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that exceptions during the enrichment process are handled correctly."""
        mock_get_config_value.side_effect = Exception("Simulated error")
        caplog.set_level(logging.ERROR)

        run_enrichment.run()

        assert "Starting enrichment process..." in caplog.text
        assert "Simulated error" not in caplog.text  # Exception should be caught
        assert "Enrichment process completed." in caplog.text
        mock_get_config_value.assert_called_once_with("api_key")
