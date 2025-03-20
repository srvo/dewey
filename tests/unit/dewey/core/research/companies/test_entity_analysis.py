from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.research.companies.entity_analysis import EntityAnalysis


class TestEntityAnalysis:
    """Unit tests for the EntityAnalysis class."""

    @pytest.fixture
    def entity_analysis(self) -> EntityAnalysis:
        """Fixture to create an EntityAnalysis instance."""
        return EntityAnalysis()

    def test_initialization(self, entity_analysis: EntityAnalysis) -> None:
        """Test the initialization of the EntityAnalysis class."""
        assert entity_analysis.name == "EntityAnalysis"
        assert entity_analysis.description == "Performs entity analysis."

    @patch("dewey.core.research.companies.entity_analysis.EntityAnalysis.get_config_value")
    @patch("dewey.core.research.companies.entity_analysis.EntityAnalysis.logger")
    def test_run_method(
        self,
        mock_logger: Any,
        mock_get_config_value: Any,
        entity_analysis: EntityAnalysis,
    ) -> None:
        """Test the run method of the EntityAnalysis class."""
        mock_get_config_value.return_value = "test_api_key"

        entity_analysis.run()

        mock_logger.info.assert_called()
        mock_logger.debug.assert_called_with("API Key: test_api_key")
        assert mock_logger.info.call_count == 2

    @patch("dewey.core.research.companies.entity_analysis.EntityAnalysis.get_config_value")
    @patch("dewey.core.research.companies.entity_analysis.EntityAnalysis.logger")
    def test_run_method_default_api_key(
        self,
        mock_logger: Any,
        mock_get_config_value: Any,
        entity_analysis: EntityAnalysis,
    ) -> None:
        """Test the run method with the default API key."""
        mock_get_config_value.return_value = None

        entity_analysis.run()

        mock_logger.info.assert_called()
        assert mock_logger.debug.call_count == 0
        assert mock_logger.info.call_count == 2
        mock_get_config_value.assert_called_with(
            "entity_analysis.api_key", default="default_key"
        )

    @patch("dewey.core.research.companies.entity_analysis.EntityAnalysis.get_config_value")
    @patch("dewey.core.research.companies.entity_analysis.EntityAnalysis.logger")
    def test_run_method_no_api_key_in_config(
        self,
        mock_logger: Any,
        mock_get_config_value: Any,
        entity_analysis: EntityAnalysis,
    ) -> None:
        """Test the run method when the API key is not in the config."""
        mock_get_config_value.return_value = "default_key"

        entity_analysis.run()

        mock_logger.info.assert_called()
        mock_logger.debug.assert_called_with("API Key: default_key")
        assert mock_logger.info.call_count == 2
        mock_get_config_value.assert_called_with(
            "entity_analysis.api_key", default="default_key"
        )
