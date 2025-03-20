import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.crm.enrichment import EnrichmentModule


class TestEnrichmentModule:
    """Test suite for the EnrichmentModule class."""

    @pytest.fixture
    def enrichment_module(self) -> EnrichmentModule:
        """Fixture to create an instance of EnrichmentModule."""
        return EnrichmentModule(name="TestEnrichment")

    def test_init(self, enrichment_module: EnrichmentModule) -> None:
        """Test the __init__ method of EnrichmentModule."""
        assert enrichment_module.name == "TestEnrichment"
        assert enrichment_module.description == "CRM Enrichment Module"
        assert isinstance(enrichment_module.logger, logging.Logger)

    def test_run(
        self, enrichment_module: EnrichmentModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method of EnrichmentModule."""
        with caplog.at_level(logging.INFO):
            enrichment_module.run()
        assert "Starting enrichment process..." in caplog.text
        assert "Example config value: default_value" in caplog.text
        assert "Enrichment process completed." in caplog.text

    def test_get_config_value(self, enrichment_module: EnrichmentModule) -> None:
        """Test the get_config_value method of EnrichmentModule."""
        # Mock the superclass's get_config_value method
        enrichment_module.get_config_value = MagicMock(return_value="test_value")  # type: ignore

        # Test retrieving an existing config value
        value = enrichment_module.get_config_value("test_key")
        assert value == "test_value"
        enrichment_module.get_config_value.assert_called_once_with("test_key", None)  # type: ignore

        # Test retrieving a config value with a default
        value = enrichment_module.get_config_value("test_key", "default_value")
        assert value == "test_value"
        enrichment_module.get_config_value.assert_called_with("test_key", "default_value")  # type: ignore

    def test_run_with_config(
        self, enrichment_module: EnrichmentModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method with a mocked configuration value."""
        # Mock the get_config_value method to return a specific value
        enrichment_module.get_config_value = MagicMock(return_value="configured_value")  # type: ignore

        with caplog.at_level(logging.INFO):
            enrichment_module.run()

        assert "Starting enrichment process..." in caplog.text
        assert "Example config value: configured_value" in caplog.text
        assert "Enrichment process completed." in caplog.text

        # Verify that get_config_value was called with the expected arguments
        enrichment_module.get_config_value.assert_called_with("example_config", "default_value")  # type: ignore
