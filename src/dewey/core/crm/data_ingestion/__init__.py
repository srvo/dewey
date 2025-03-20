from dewey.core.base_script import BaseScript
import logging
from typing import Any

class DataIngestionModule(BaseScript):
    """
    A module for managing data ingestion tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for data ingestion scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, name: str, description: str = "Data Ingestion Module"):
        """
        Initializes the DataIngestionModule.

        Args:
            name (str): The name of the module.
            description (str, optional): A description of the module.
                Defaults to "Data Ingestion Module".
        """
        super().__init__(name, description)

    def run(self) -> None:
        """
        Executes the primary logic of the data ingestion module.
        """
        self.logger.info("Starting data ingestion process...")

        # Example of accessing a configuration value
        data_source = self.get_config_value("data_source", "default_source")
        self.logger.info(f"Using data source: {data_source}")

        # Add your data ingestion logic here
        self.logger.info("Data ingestion process completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key (str): The key of the configuration value to retrieve.
            default (Any, optional): A default value to return if the key
                is not found in the configuration. Defaults to None.

        Returns:
            Any: The configuration value associated with the key, or the
                default value if the key is not found.
        """
        return super().get_config_value(key, default)
