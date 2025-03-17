import logging

from research.workflows.ethical import EthicalAnalysisWorkflow

logging.basicConfig(level=logging.INFO)


def run_exclusions_workflow():
    """
    Run the exclusions workflow to identify companies that should be excluded from the investment universe.
    """


if __name__ == "__main__":
    workflow = EthicalAnalysisWorkflow()
    workflow.execute()
