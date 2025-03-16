```python
from typing import Any, Dict, List

from ethifinx.api_client import APIClient
from ethifinx.data_processor import DataProcessor
from ethifinx.db.data_store import DataStore
from ethifinx.research.workflow import Workflow, WorkflowPhase
from logger import setup_logger

logger = setup_logger("example_workflow", "logs/example_workflow.log")


def fetch_data(query: str) -> Dict[str, Any]:
    """Fetch data from the API.

    Args:
        query: The search query.

    Returns:
        The fetched data.
    """
    api_client = APIClient()
    return api_client.fetch_data("search_endpoint", params={"query": query})


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process raw data into a structured format.

    Args:
        data: The raw data to process.

    Returns:
        The processed data.
    """
    processor = DataProcessor()
    return processor.process(data)


def save_data(processed_data: Dict[str, Any]) -> None:
    """Save processed data to the database and back it up to S3.

    Args:
        processed_data: The processed data to save.
    """
    data_store = DataStore()
    data_store.save_to_db(processed_data)
    data_store.backup_to_s3("data/research.db")


def define_workflow_phases() -> List[WorkflowPhase]:
    """Define the workflow phases.

    Returns:
        A list of WorkflowPhase objects.
    """
    return [
        WorkflowPhase(name="Fetch Data", task=fetch_data, args={"query": "test query"}),
        WorkflowPhase(name="Process Data", task=process_data),
        WorkflowPhase(name="Save Data", task=save_data),
    ]


def execute_workflow(phases: List[WorkflowPhase]) -> List[Any]:
    """Create and execute the workflow.

    Args:
        phases: A list of WorkflowPhase objects.

    Returns:
        A list of results from each phase.
    """
    workflow = Workflow(phases, n_jobs=1)
    results = workflow.execute()
    return results


def observe_workflow_progress(workflow: Workflow) -> None:
    """Observe the workflow's progress and log the results.

    Args:
        workflow: The Workflow object to observe.
    """
    for result in workflow.observe():
        logger.info(f"Phase result: {result}")


def main() -> None:
    """Main function to orchestrate the workflow."""
    phases = define_workflow_phases()
    execute_workflow(phases)

    workflow = Workflow(phases, n_jobs=1)
    workflow.execute()
    observe_workflow_progress(workflow)


if __name__ == "__main__":
    main()
```
