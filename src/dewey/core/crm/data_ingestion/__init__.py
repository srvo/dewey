from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
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

    def __init__(self, name: str, description: str = "Data Ingestion Module") -> None:
        """
        Initializes the DataIngestionModule.

        Args:
            name: The name of the module.
            description: A description of the module.
                Defaults to "Data Ingestion Module".
        """
        super().__init__(name, description, config_section="data_ingestion")

    def run(self) -> None:
        """
        Executes the primary logic of the data ingestion module.
        """
        self.logger.info("Starting data ingestion process...")

        # Example of accessing a configuration value
        data_source = self.get_config_value("data_source", "default_source")
        self.logger.info(f"Using data source: {data_source}")

        # Add your data ingestion logic here
        # Example database connection
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.logger.info(f"Database connection test: {result}")
        except Exception as e:
            self.logger.error(f"Database error: {e}")

        # Example LLM usage
        try:
            response = self.llm_client.generate_text("Tell me a joke.")
            self.logger.info(f"LLM response: {response}")
        except Exception as e:
            self.logger.error(f"LLM error: {e}")

        self.logger.info("Data ingestion process completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key: The key of the configuration value to retrieve.
            default: A default value to return if the key
                is not found in the configuration. Defaults to None.

        Returns:
            The configuration value associated with the key, or the
            default value if the key is not found.
        """
        return super().get_config_value(key, default)
