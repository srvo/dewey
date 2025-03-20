from typing import Any, Optional, Protocol

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class LLMClientInterface(Protocol):
    """Interface for LLM clients."""

    def generate_text(self, prompt: str) -> str:
        ...


class DatabaseConnectionInterface(Protocol):
    """Interface for Database connections."""

    def execute(self, query: str, parameters: dict = {}) -> Any:
        ...

    def close(self) -> None:
        ...

    def __enter__(self) -> Any:
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        ...


class AutomationModule(BaseScript):
    """
    Base class for automation modules within Dewey.

    This class provides a standardized structure for automation scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(
        self,
        config_section: str = "automation",
        db_conn: Optional[DatabaseConnectionInterface] = None,
        llm_client: Optional[LLMClientInterface] = None,
    ) -> None:
        """
        Initializes the AutomationModule.

        Args:
            config_section: The configuration section to use for this module.
            db_conn: Optional database connection.  Defaults to None, which will use the BaseScript's default.
            llm_client: Optional LLM client. Defaults to None, which will use the BaseScript's default.
        """
        super().__init__(config_section=config_section, requires_db=True, enable_llm=True)
        self._db_conn = db_conn or self.db_conn
        self._llm_client = llm_client or self.llm_client

    def _get_example_config_value(self) -> str:
        """
        Gets the example config value.  This is separated out to allow for easier testing.
        """
        return self.get_config_value("example_config_key", "default_value")

    def _execute_database_query(self, conn: DatabaseConnectionInterface) -> Any:
        """
        Executes the example database query.  This is separated out to allow for easier testing.
        """
        return conn.execute("SELECT 1")

    def _generate_llm_response(self, llm_client: LLMClientInterface) -> str:
        """
        Generates the LLM response.  This is separated out to allow for easier testing.
        """
        prompt = "Write a short poem about automation."
        return llm_client.generate_text(prompt)

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
            config_value = self._get_example_config_value()
            self.logger.info(f"Example config value: {config_value}")

            # Example usage of database connection
            if self._db_conn:
                with self._db_conn as conn:  # Use context manager for connection
                    # Example query (replace with your actual query)
                    result = self._execute_database_query(conn)
                    self.logger.info(f"Database query result: {result}")
            else:
                self.logger.warning("Database connection not available.")

            # Example usage of LLM client
            if self._llm_client:
                response = self._generate_llm_response(self._llm_client)
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
