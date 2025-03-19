from dewey.core.base_script import BaseScript
from typing import Any, Dict


class DataIngestionAgent(BaseScript):
    """
    A Dewey script for data ingestion tasks.

    This agent handles the process of ingesting data from various sources,
    transforming it, and loading it into a target system.
    """

    def __init__(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """
        Initializes the DataIngestionAgent.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config=config, **kwargs)

    def run(self) -> None:
        """
        Executes the data ingestion process.

        This method orchestrates the data ingestion workflow, including
        extracting data from sources, transforming it according to defined rules,
        and loading it into the designated target system.

        Raises:
            Exception: If any error occurs during the data ingestion process.
        """
        try:
            self.logger.info("Starting data ingestion process...")

            # Example of accessing configuration values
            source_type = self.get_config_value("source_type")
            self.logger.info(f"Source type: {source_type}")

            # Add your data ingestion logic here
            self.logger.info("Data ingestion completed successfully.")

        except Exception as e:
            self.logger.exception(f"An error occurred during data ingestion: {e}")
            raise
