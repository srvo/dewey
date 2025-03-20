import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.enrichment.test_enrichment import TestEnrichment


class TestTestEnrichment:
    """Unit tests for the TestEnrichment class."""

    @pytest.fixture
    def test_enrichment(self) -> TestEnrichment:
        """Fixture to create a TestEnrichment instance."""
        return TestEnrichment()

    def test_initialization(self, test_enrichment: TestEnrichment) -> None:
        """Test that the TestEnrichment instance is initialized correctly."""
        assert isinstance(test_enrichment, TestEnrichment)
        assert isinstance(test_enrichment, BaseScript)
        assert test_enrichment.name == "TestEnrichment"
        assert test_enrichment.description == "Tests the CRM enrichment process."
        assert test_enrichment.config_section == "test_enrichment"

    @patch("dewey.core.crm.enrichment.test_enrichment.TestEnrichment.get_config_value")
    @patch("dewey.core.crm.enrichment.test_enrichment.TestEnrichment.logger")
    def test_run_success(
        self, mock_logger: Any, mock_get_config_value: Any, test_enrichment: TestEnrichment
    ) -> None:
        """Test the run method executes successfully."""
        mock_get_config_value.return_value = "test_value"
        test_enrichment.run()

        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 3
        mock_get_config_value.assert_called_once_with("example_config", "default_value")

    @patch("dewey.core.crm.enrichment.test_enrichment.TestEnrichment.get_config_value")
    @patch("dewey.core.crm.enrichment.test_enrichment.TestEnrichment.logger")
    def test_run_config_error(
        self, mock_logger: Any, mock_get_config_value: Any, test_enrichment: TestEnrichment
    ) -> None:
        """Test the run method handles configuration errors."""
        mock_get_config_value.side_effect = Exception("Config error")
        with pytest.raises(Exception, match="Config error"):
            test_enrichment.run()

        mock_logger.info.assert_called_once_with("Starting test enrichment process.")
        mock_get_config_value.assert_called_once_with("example_config", "default_value")

    @patch("dewey.core.crm.enrichment.test_enrichment.TestEnrichment.get_config_value")
    @patch("dewey.core.crm.enrichment.test_enrichment.TestEnrichment.logger")
    def test_run_no_error(
        self, mock_logger: Any, mock_get_config_value: Any, test_enrichment: TestEnrichment
    ) -> None:
        """Test the run method executes successfully without error."""
        mock_get_config_value.return_value = "test_value"
        test_enrichment.run()

        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 3
        mock_get_config_value.assert_called_once_with("example_config", "default_value")
