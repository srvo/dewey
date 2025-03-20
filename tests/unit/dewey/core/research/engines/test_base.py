import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.research.engines.base import BaseEngine


class TestBaseEngine:
    """Unit tests for the BaseEngine class."""

    @pytest.fixture
    def base_engine(self) -> BaseEngine:
        """Fixture for creating a BaseEngine instance."""
        return BaseEngine(name="TestEngine", description="A test engine")

    def test_init(self, base_engine: BaseEngine) -> None:
        """Test the __init__ method."""
        assert base_engine.name == "TestEngine"
        assert base_engine.description == "A test engine"
        assert base_engine.config_section == "engines"
        assert base_engine.templates == {}
        assert base_engine.logger is not None

    def test_run_not_implemented(self, base_engine: BaseEngine) -> None:
        """Test that the run method raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            base_engine.run()
        assert str(exc_info.value) == "The run method must be implemented in the subclass."

    def test_add_template(self, base_engine: BaseEngine) -> None:
        """Test the add_template method."""
        base_engine.add_template(name="test_template", template="This is a test template.")
        assert base_engine.templates["test_template"] == "This is a test template."
        # Verify that the logger was called with the correct message
        assert "Adding template: test_template" in base_engine.logger.mock_calls[0].__str__()

    def test_get_template(self, base_engine: BaseEngine) -> None:
        """Test the get_template method."""
        base_engine.add_template(name="test_template", template="This is a test template.")
        template = base_engine.get_template(name="test_template")
        assert template == "This is a test template."
        # Verify that the logger was called with the correct message
        assert "Getting template: test_template" in base_engine.logger.mock_calls[1].__str__()

        template = base_engine.get_template(name="nonexistent_template")
        assert template is None
        # Verify that the logger was called with the correct message
        assert "Getting template: nonexistent_template" in base_engine.logger.mock_calls[2].__str__()

    def test_search(self, base_engine: BaseEngine) -> None:
        """Test the search method."""
        query = "test query"
        results = base_engine.search(query=query)
        assert results == []
        # Verify that the logger was called with the correct message
        assert f"Searching for: {query}" in base_engine.logger.mock_calls[0].__str__()

    def test_analyze_template_found(self, base_engine: BaseEngine) -> None:
        """Test the analyze method when the template is found."""
        base_engine.add_template(name="test_template", template="This is a test template with {variable}.")
        result = base_engine.analyze(template_name="test_template", variable="test")
        assert result == "This is a test template with test."
        # Verify that the logger was called with the correct messages
        assert "Analyzing with template: test_template" in base_engine.logger.mock_calls[0].__str__()
        assert "Formatted template: This is a test template with test." in base_engine.logger.mock_calls[2].__str__()

    def test_analyze_template_not_found(self, base_engine: BaseEngine) -> None:
        """Test the analyze method when the template is not found."""
        result = base_engine.analyze(template_name="nonexistent_template")
        assert result == "No template found with name: nonexistent_template"
        # Verify that the logger was called with the correct messages
        assert "Analyzing with template: nonexistent_template" in base_engine.logger.mock_calls[0].__str__()
        assert "No template found with name: nonexistent_template" in base_engine.logger.mock_calls[1].__str__()

    def test_analyze_missing_variable(self, base_engine: BaseEngine) -> None:
        """Test the analyze method when a required variable is missing."""
        base_engine.add_template(name="test_template", template="This is a test template with {missing_variable}.")
        result = base_engine.analyze(template_name="test_template")
        assert "Missing required variable: 'missing_variable'" in result
        # Verify that the logger was called with the correct messages
        assert "Analyzing with template: test_template" in base_engine.logger.mock_calls[0].__str__()
        assert "Missing required variable: 'missing_variable'" in base_engine.logger.mock_calls[2].__str__()

    def test_analyze_formatting_error(self, base_engine: BaseEngine) -> None:
        """Test the analyze method when there is an error formatting the template."""
        base_engine.add_template(name="test_template", template="This is a test template with a malformed {template")
        result = base_engine.analyze(template_name="test_template")
        assert "Error formatting template: unexpected end of string while looking for matching `}'" in result
        # Verify that the logger was called with the correct messages
        assert "Analyzing with template: test_template" in base_engine.logger.mock_calls[0].__str__()
        assert "Error formatting template: unexpected end of string while looking for matching `}'" in result

    @pytest.fixture(autouse=True)
    def mock_logger(self, base_engine: BaseEngine):
        """Fixture to mock the logger for each test."""
        base_engine.logger = MagicMock(spec=logging.Logger)
        yield
