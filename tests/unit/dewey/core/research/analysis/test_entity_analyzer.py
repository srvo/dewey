import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.research.analysis.entity_analyzer import EntityAnalyzer


class TestEntityAnalyzer:
    """Test suite for the EntityAnalyzer class."""

    @pytest.fixture
    def entity_analyzer(self) -> EntityAnalyzer:
        """Fixture to create an instance of EntityAnalyzer with mocked dependencies."""
        analyzer = EntityAnalyzer()
        analyzer.logger = MagicMock(spec=logging.Logger)  # Mock the logger
        return analyzer

    def test_init(self, entity_analyzer: EntityAnalyzer) -> None:
        """Test the __init__ method of EntityAnalyzer."""
        assert entity_analyzer.name == "EntityAnalyzer"
        assert entity_analyzer.config_section == "entity_analyzer"
        assert entity_analyzer.logger is not None

    def test_run(self, entity_analyzer: EntityAnalyzer) -> None:
        """Test the run method of EntityAnalyzer."""
        entity_analyzer.get_config_value = MagicMock(return_value="test_key")
        entity_analyzer.run()

        entity_analyzer.logger.info.assert_called_with("Entity analysis completed.")
        entity_analyzer.logger.debug.assert_called_with("API Key: test_key")
        entity_analyzer.get_config_value.assert_called_with("api_key", default="default_key")

    def test_analyze_text(self, entity_analyzer: EntityAnalyzer) -> None:
        """Test the analyze_text method of EntityAnalyzer."""
        text = "This is a test text with John and Jane from Example Corp."
        expected_entities = {"PERSON": ["John", "Jane"], "ORG": ["Example Corp"]}
        result = entity_analyzer.analyze_text(text)

        assert result == expected_entities
        entity_analyzer.logger.info.assert_called_with("Text analysis completed.")

    def test_analyze_text_empty(self, entity_analyzer: EntityAnalyzer) -> None:
        """Test the analyze_text method with empty text."""
        text = ""
        expected_entities = {"PERSON": ["John", "Jane"], "ORG": ["Example Corp"]}  # Default return
        result = entity_analyzer.analyze_text(text)

        assert result == expected_entities
        entity_analyzer.logger.info.assert_called_with("Text analysis completed.")

    def test_analyze_text_special_characters(self, entity_analyzer: EntityAnalyzer) -> None:
        """Test the analyze_text method with special characters in the text."""
        text = "This is a test with !@#$%^&*()_+=-`~[]\{}|;':\",./<>?"
        expected_entities = {"PERSON": ["John", "Jane"], "ORG": ["Example Corp"]}  # Default return
        result = entity_analyzer.analyze_text(text)

        assert result == expected_entities
        entity_analyzer.logger.info.assert_called_with("Text analysis completed.")

    def test_analyze_text_long_text(self, entity_analyzer: EntityAnalyzer) -> None:
        """Test the analyze_text method with a very long text."""
        text = "A" * 2000
        expected_entities = {"PERSON": ["John", "Jane"], "ORG": ["Example Corp"]}  # Default return
        result = entity_analyzer.analyze_text(text)

        assert result == expected_entities
        entity_analyzer.logger.info.assert_called_with("Text analysis completed.")
