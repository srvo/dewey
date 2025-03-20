from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient
from typing import Protocol


class DatabaseConnectionInterface(Protocol):
    """
    Interface for database connections, enabling mocking.
    """
    def execute(self, query: str) -> None:
        ...


class LLMClientInterface(Protocol):
    """
    Interface for LLM clients, enabling mocking.
    """
    def generate_text(self, prompt: str) -> str:
        ...


class AnalyzeArchitecture(BaseScript):
    """
    Analyzes the architecture of the Dewey system.

    This script provides functionality to analyze and report on the
    overall architecture, dependencies, and key components of the Dewey system.
    """

    def __init__(
        self,
        db_connection: DatabaseConnectionInterface | None = None,
        llm_client: LLMClientInterface | None = None,
    ) -> None:
        """Initializes the AnalyzeArchitecture script."""
        super().__init__(
            config_section="analyze_architecture", requires_db=True, enable_llm=True
        )
        self._db_connection = db_connection
        self._llm_client = llm_client

    def _get_db_connection(self) -> DatabaseConnectionInterface:
        """
        Internal method to get the database connection.

        Returns:
            DatabaseConnectionInterface: The database connection object.
        """
        if self._db_connection is None:
            return DatabaseConnection(self.config)
        return self._db_connection

    def _get_llm_client(self) -> LLMClientInterface:
        """
        Internal method to get the LLM client.

        Returns:
            LLMClientInterface: The LLM client object.
        """
        if self._llm_client is None:
            return self.llm_client
        return self._llm_client

    def run(self) -> None:
        """
        Executes the architecture analysis process.

        This method orchestrates the analysis of the system architecture,
        collects relevant data, and generates a report.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any error occurs during the analysis.
        """
        self.logger.info("Starting architecture analysis...")

        # Example of accessing a configuration value
        example_config_value = self.get_config_value("utils.example_config")
        self.logger.info(f"Example config value: {example_config_value}")

        # Example of using the database connection
        try:
            db_conn = self._get_db_connection()
            with db_conn:
                db_conn.execute("SELECT 1;")
                self.logger.info("Database connection test successful.")
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")

        # Example of using the LLM client
        try:
            llm_client = self._get_llm_client()
            response = llm_client.generate_text("Explain the Dewey system architecture.")
            self.logger.info(f"LLM response: {response}")
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")

        # Add your architecture analysis logic here
        self.logger.info("Architecture analysis completed.")


if __name__ == "__main__":
    analyzer = AnalyzeArchitecture()
    analyzer.execute()
