# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:33:42 2025

from unittest.mock import Mock

import pytest
from ethifinx.research.workflow import Workflow, WorkflowPhase


@pytest.fixture()
def mock_phases():
    """Fixture to create mock workflow phases."""
    return [
        WorkflowPhase(name="Phase 1", task=Mock(return_value="Result 1")),
        WorkflowPhase(name="Phase 2", task=Mock(return_value="Result 2")),
        WorkflowPhase(name="Phase 3", task=Mock(return_value="Result 3")),
    ]


def test_workflow_phase_execute_success(mock_phases) -> None:
    """Test successful execution of a workflow phase."""
    phase = mock_phases[0]
    result = phase.execute()
    assert result == "Result 1"
    phase.task.assert_called_once()


def test_workflow_phase_execute_failure(mock_phases) -> None:
    """Test workflow phase execution failure."""
    phase = mock_phases[0]
    phase.task.side_effect = Exception("Task Error")
    with pytest.raises(Exception):
        phase.execute()


def test_workflow_execute_success(mock_phases) -> None:
    """Test successful execution of a workflow."""
    workflow = Workflow(mock_phases, n_jobs=1)
    results = workflow.execute()
    assert results == ["Result 1", "Result 2", "Result 3"]


def test_workflow_execute_failure(mock_phases) -> None:
    """Test workflow execution failure."""
    mock_phases[1].task.side_effect = Exception("Phase 2 Error")
    workflow = Workflow(mock_phases, n_jobs=1)
    with pytest.raises(Exception):
        workflow.execute()


def test_workflow_observe(mock_phases) -> None:
    """Test observing workflow progress."""
    workflow = Workflow(mock_phases, n_jobs=1)
    observed_results = list(workflow.observe())
    assert observed_results == ["Result 1", "Result 2", "Result 3"]
