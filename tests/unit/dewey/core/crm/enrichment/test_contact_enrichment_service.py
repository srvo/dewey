import logging
from unittest.mock import patch

import pytest

from dewey.core.crm.enrichment.contact_enrichment_service import (
    ContactEnrichmentService,
)


class TestContactEnrichmentService:
    """Unit tests for the ContactEnrichmentService class."""

    @pytest.fixture
    def enrichment_service(self, caplog):
        """Fixture to create a ContactEnrichmentService instance."""
        caplog.set_level(logging.INFO)
        return ContactEnrichmentService()

    def test_init(self, enrichment_service):
        """Test the __init__ method."""
        assert enrichment_service.config_section == "crm.enrichment"

    def test_run_success(self, enrichment_service, caplog):
        """Test the run method with a valid API key."""
        with patch.object(
            enrichment_service, "get_config_value", return_value="test_api_key"
        ) as mock_get_config_value:
            enrichment_service.run()

            mock_get_config_value.assert_called_once_with("enrichment_api_key")
            assert "Starting contact enrichment process." in caplog.text
            assert "Using API key: test_api_key" in caplog.text
            assert "Contact enrichment process completed." in caplog.text

    def test_run_no_api_key(self, enrichment_service, caplog):
        """Test the run method when the API key is not found in the config."""
        with patch.object(
            enrichment_service, "get_config_value", return_value=None
        ) as mock_get_config_value:
            enrichment_service.run()

            mock_get_config_value.assert_called_once_with("enrichment_api_key")
            assert "Starting contact enrichment process." in caplog.text
            assert "Enrichment API key not found in config." in caplog.text
            assert "Contact enrichment process completed." not in caplog.text

    def test_run_empty_api_key(self, enrichment_service, caplog):
        """Test the run method when the API key is an empty string."""
        with patch.object(
            enrichment_service, "get_config_value", return_value=""
        ) as mock_get_config_value:
            enrichment_service.run()

            mock_get_config_value.assert_called_once_with("enrichment_api_key")
            assert "Starting contact enrichment process." in caplog.text
            assert "Enrichment API key not found in config." in caplog.text
            assert "Contact enrichment process completed." not in caplog.text
