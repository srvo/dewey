import logging
from unittest.mock import patch

import pytest

from dewey.core.research.workflows import ResearchWorkflow


class TestResearchWorkflow:
    """Tests for the ResearchWorkflow class."""

    @pytest.fixture
    def research_workflow(self) -> ResearchWorkflow:
        """Fixture for creating a ResearchWorkflow instance."""
        return ResearchWorkflow(name="Test Workflow", description="A test workflow")

    def test_init(self, research_workflow: ResearchWorkflow) -> None:
        """Tests the __init__ method."""
        assert research_workflow.name == "Test Workflow"
        assert research_workflow.description == "A test workflow"
        assert research_workflow.logger.name == "Test Workflow"

    def test_run(self, research_workflow: ResearchWorkflow, caplog: pytest.LogCaptureFixture) -> None:
        """Tests the run method."""
        with caplog.at_level(logging.INFO):
            research_workflow.run()
        assert f"Running research workflow: {research_workflow.name}" in caplog.text

    def test_get_config_value(self, research_workflow: ResearchWorkflow) -> None:
        """Tests the get_config_value method."""
        # Mock the config attribute to avoid loading the actual config file
        research_workflow.config = {"test_key": "test_value"}
        value = research_workflow.get_config_value("test_key")
        assert value == "test_value"

        # Test with a default value
        value = research_workflow.get_config_value("non_existent_key", "default_value")
        assert value == "default_value"

        # Test with a nested key
        research_workflow.config = {"nested": {"test_key": "nested_value"}}
        value = research_workflow.get_config_value("nested.test_key")
        assert value == "nested_value"

        # Test when the nested key does not exist
        value = research_workflow.get_config_value("nested.non_existent_key", "default_value")
        assert value == "default_value"

        # Test when the first level key does not exist
        value = research_workflow.get_config_value("non_existent.test_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_no_config(self, research_workflow: ResearchWorkflow) -> None:
        """Tests the get_config_value method when config is None."""
        research_workflow.config = None  # type: ignore[assignment]
        value = research_workflow.get_config_value("test_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_empty_config(self, research_workflow: ResearchWorkflow) -> None:
        """Tests the get_config_value method when config is an empty dictionary."""
        research_workflow.config = {}
        value = research_workflow.get_config_value("test_key", "default_value")
        assert value == "default_value"

    def test_inheritance_from_base_script(self, research_workflow: ResearchWorkflow) -> None:
        """Tests that ResearchWorkflow inherits from BaseScript."""
        assert isinstance(research_workflow, ResearchWorkflow)
        assert hasattr(research_workflow, 'logger')
        assert hasattr(research_workflow, 'config')

    @patch("dewey.core.research.workflows.ResearchWorkflow.logger")
    def test_run_with_mocked_logger(self, mock_logger, research_workflow: ResearchWorkflow) -> None:
        """Tests the run method with a mocked logger."""
        research_workflow.run()
        mock_logger.info.assert_called_once_with(f"Running research workflow: {research_workflow.name}")
