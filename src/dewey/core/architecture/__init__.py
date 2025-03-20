from abc import ABC, abstractmethod
from typing import Optional

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm.llm_utils import generate_text


class DatabaseInterface(ABC):
    """
    An interface for database operations, enabling mocking.
    """

    @abstractmethod
    def execute(self, query: str):
        """Execute a database query."""
        pass


class ConcreteDatabase(DatabaseInterface):
    """
    A concrete implementation of the DatabaseInterface using DatabaseConnection.
    """

    def __init__(self, config):
        self.config = config

    def execute(self, query: str):
        with DatabaseConnection(self.config) as db_conn:
            result_df = db_conn.execute(query)
            return result_df


class ArchitectureModule(BaseScript):
    """
    A module for architecture-related functionalities within the Dewey system.

    This module inherits from BaseScript and provides standardized access to
    configuration, logging, and other common utilities.
    """

    def __init__(
        self,
        db: Optional[DatabaseInterface] = None,
        llm_generate_text=generate_text,
    ) -> None:
        """
        Initializes the ArchitectureModule.
        """
        super().__init__(
            config_section="architecture", requires_db=True, enable_llm=True
        )
        self.logger.info("Architecture module initialized.")
        self._db: DatabaseInterface = db if db is not None else ConcreteDatabase(self.config)
        self._llm_generate_text = llm_generate_text

    def _get_example_config_value(self) -> str:
        """
        Retrieves the example configuration value.
        """
        return self.get_config_value("utils.example_config", default="default_value")

    def _execute_database_query(self) -> None:
        """
        Executes a sample database query.
        """
        if self.db_conn:
            self.logger.info("Database connection is available.")
            result_df = self._db.execute("SELECT 1")
            self.logger.info(f"Database query result: {result_df}")
        else:
            self.logger.warning("Database connection is not available.")

    def _generate_llm_response(self) -> None:
        """
        Generates a response from the LLM.
        """
        if self.llm_client:
            self.logger.info("LLM client is available.")
            prompt = "Write a short poem about architecture."
            response = self._llm_generate_text(self.llm_client, prompt)
            self.logger.info(f"LLM response: {response}")
        else:
            self.logger.warning("LLM client is not available.")

    def run(self) -> None:
        """
        Executes the main logic of the architecture module.

        This method demonstrates accessing configuration values, utilizing
        database connections, and interacting with LLM functionalities.

        Raises:
            Exception: If an error occurs during module execution.
        """
        try:
            # Accessing a configuration value
            example_config_value = self._get_example_config_value()
            self.logger.info(f"Example config value: {example_config_value}")

            # Example: Using the database connection
            self._execute_database_query()

            # Example: Using the LLM client
            self._generate_llm_response()

            # Add your main logic here
            self.logger.info("Architecture module run method executed.")

        except Exception as e:
            self.logger.exception(
                f"An error occurred during architecture module execution: {e}"
            )

