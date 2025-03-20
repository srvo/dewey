from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm.llm_utils import generate_text


class ArchitectureModule(BaseScript):
    """
    A module for architecture-related functionalities within the Dewey system.

    This module inherits from BaseScript and provides standardized access to
    configuration, logging, and other common utilities.
    """

    def __init__(self) -> None:
        """
        Initializes the ArchitectureModule.
        """
        super().__init__(
            config_section="architecture", requires_db=True, enable_llm=True
        )
        self.logger.info("Architecture module initialized.")

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
            example_config_value: str = self.get_config_value(
                "utils.example_config", default="default_value"
            )
            self.logger.info(f"Example config value: {example_config_value}")

            # Example: Using the database connection
            if self.db_conn:
                self.logger.info("Database connection is available.")
                # Example: Execute a query (replace with actual query)
                with DatabaseConnection(self.config) as db_conn:
                    result_df = db_conn.execute("SELECT 1")
                    self.logger.info(f"Database query result: {result_df}")
            else:
                self.logger.warning("Database connection is not available.")

            # Example: Using the LLM client
            if self.llm_client:
                self.logger.info("LLM client is available.")
                # Example: Generate text (replace with actual prompt)
                prompt = "Write a short poem about architecture."
                response = generate_text(self.llm_client, prompt)
                self.logger.info(f"LLM response: {response}")
            else:
                self.logger.warning("LLM client is not available.")

            # Add your main logic here
            self.logger.info("Architecture module run method executed.")

        except Exception as e:
            self.logger.exception(
                f"An error occurred during architecture module execution: {e}"
            )
