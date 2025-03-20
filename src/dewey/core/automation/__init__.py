from typing import Any

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class AutomationModule(BaseScript):
    """
    Base class for automation modules within Dewey.

    This class provides a standardized structure for automation scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(self, config_section: str = "automation") -> None:
        """
        Initializes the AutomationModule.

        Args:
            config_section: The configuration section to use for this module.
        """
        super().__init__(config_section=config_section, requires_db=True, enable_llm=True)

    def run(self) -> None:
        """
        Executes the main logic of the automation module.

        This method should be overridden by subclasses to implement
        the specific automation tasks.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If something goes wrong.
        """
        self.logger.info("Automation module started.")

        try:
            # Example usage of config value
            config_value = self.get_config_value("example_config_key", "default_value")
            self.logger.info(f"Example config value: {config_value}")

            # Example usage of database connection
            if self.db_conn:
                with self.db_conn as conn:  # Use context manager for connection
                    # Example query (replace with your actual query)
                    result = conn.execute("SELECT 1")
                    self.logger.info(f"Database query result: {result}")
            else:
                self.logger.warning("Database connection not available.")

            # Example usage of LLM client
            if self.llm_client:
                prompt = "Write a short poem about automation."
                response = self.llm_client.generate_text(prompt)
                self.logger.info(f"LLM response: {response}")
            else:
                self.logger.warning("LLM client not available.")

        except Exception as e:
            self.logger.error(f"An error occurred during automation: {e}", exc_info=True)
            raise

        self.logger.info("Automation module finished.")


if __name__ == "__main__":
    # Example usage:
    automation_module = AutomationModule()
    automation_module.execute()
