from ethifinx.research.workflow import Workflow, WorkflowPhase
from ethifinx.api_client import APIClient
from ethifinx.db.data_store import DataStore
from ethifinx.data_processor import DataProcessor
from logger import setup_logger

logger = setup_logger("example_workflow", "logs/example_workflow.log")


def fetch_data(query: str):
    """
    Fetch data from the API.

    Args:
        query (str): The search query.

    Returns:
        Dict: The fetched data.
    """
    api_client = APIClient()
    return api_client.fetch_data("search_endpoint", params={"query": query})


def process_data(data):
    """
    Process raw data into a structured format.

    Args:
        data (Dict): The raw data to process.

    Returns:
        Dict: The processed data.
    """
    processor = DataProcessor()
    return processor.process(data)


def save_data(processed_data):
    """
    Save processed data to the database and back it up to S3.

    Args:
        processed_data (Dict): The processed data to save.
    """
    data_store = DataStore()
    data_store.save_to_db(processed_data)
    data_store.backup_to_s3("data/research.db")


# Define workflow phases
phases = [
    WorkflowPhase(name="Fetch Data", task=fetch_data, args={"query": "test query"}),
    WorkflowPhase(name="Process Data", task=process_data),
    WorkflowPhase(name="Save Data", task=save_data),
]

# Create and execute the workflow
workflow = Workflow(phases, n_jobs=1)
results = workflow.execute()

# Observe the workflow's progress
for result in workflow.observe():
    logger.info(f"Phase result: {result}")
