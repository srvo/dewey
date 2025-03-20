import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.research.utils.analysis_tagging_workflow import AnalysisTaggingWorkflow


class TestAnalysisTaggingWorkflow:
    """Tests for the AnalysisTaggingWorkflow class."""

    @pytest.fixture
    def analysis_tagging_workflow(self) -> AnalysisTaggingWorkflow:
        """Fixture for creating an AnalysisTaggingWorkflow instance."""
        return AnalysisTaggingWorkflow()

    def test_init(self) -> None:
        """Tests the __init__ method."""
        workflow = AnalysisTaggingWorkflow(
            config_section="test_section", requires_db=True, enable_llm=True
        )
        assert workflow.config_section == "test_section"
        assert workflow.requires_db is True
        assert workflow.enable_llm is True
        assert workflow.name == "AnalysisTaggingWorkflow"
        assert workflow.logger is not None

    @patch(
        "dewey.core.research.utils.analysis_tagging_workflow.AnalysisTaggingWorkflow.get_config_value"
    )
    def test_run_tagging_enabled(
        self,
        mock_get_config_value: Any,
        analysis_tagging_workflow: AnalysisTaggingWorkflow,
        caplog: Any,
    ) -> None:
        """Tests the run method when tagging is enabled."""
        mock_get_config_value.return_value = True
        with caplog.atLevel(logging.INFO):
            analysis_tagging_workflow.run()
        assert "Starting analysis tagging workflow." in caplog.text
        assert "Analysis tagging is enabled." in caplog.text
        mock_get_config_value.assert_called_once_with("analysis.tagging.enabled", True)

    @patch(
        "dewey.core.research.utils.analysis_tagging_workflow.AnalysisTaggingWorkflow.get_config_value"
    )
    def test_run_tagging_disabled(
        self,
        mock_get_config_value: Any,
        analysis_tagging_workflow: AnalysisTaggingWorkflow,
        caplog: Any,
    ) -> None:
        """Tests the run method when tagging is disabled."""
        mock_get_config_value.return_value = False
        with caplog.atLevel(logging.INFO):
            analysis_tagging_workflow.run()
        assert "Starting analysis tagging workflow." in caplog.text
        assert "Analysis tagging is disabled." in caplog.text
        mock_get_config_value.assert_called_once_with("analysis.tagging.enabled", True)

    @patch(
        "dewey.core.research.utils.analysis_tagging_workflow.AnalysisTaggingWorkflow.get_config_value"
    )
    def test_run_config_exception(
        self,
        mock_get_config_value: Any,
        analysis_tagging_workflow: AnalysisTaggingWorkflow,
        caplog: Any,
    ) -> None:
        """Tests the run method when there is an exception getting the config value."""
        mock_get_config_value.side_effect = Exception("Config error")
        with caplog.atLevel(logging.ERROR):
            analysis_tagging_workflow.run()
        assert "Starting analysis tagging workflow." in caplog.text
        mock_get_config_value.assert_called_once_with("analysis.tagging.enabled", True)
