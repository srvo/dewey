from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm.llm_utils import generate
from typing import Any, Dict, Optional, Protocol
import sys

class LLMClientInterface(Protocol):
    """
    Interface for LLM clients, enabling mocking for testing.
    """
    def generate(self, prompt: str) -> str:
        ...

class AnalysisScript(BaseScript):
    """
    Base class for analysis scripts in the Dewey project.

    This class provides a standardized way to access configuration, logging,
    database connections, and LLM integrations. It inherits from BaseScript
    and implements the abstract run method.

    Attributes:
        name (str): Name of the script (used for logging).
        description (str): Description of the script.
        logger (logging.Logger): Configured logger instance.
        config (Dict[str, Any]): Loaded configuration from dewey.yaml.
        db_conn (DatabaseConnection): Database connection (if enabled).
        llm_client: LLM client (if enabled).
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config_section: Optional[str] = None,
        requires_db: bool = False,
        enable_llm: bool = False,
        db_connection_getter = get_connection,
        llm_client: Optional[LLMClientInterface] = None,
    ) -> None:
        """
        Initialize the AnalysisScript.

        Args:
            name (Optional[str]): Name of the script (used for logging).
                Defaults to the class name.
            description (Optional[str]): Description of the script.
                Defaults to None.
            config_section (Optional[str]): Section in dewey.yaml to load
                for this script. Defaults to None.
            requires_db (bool): Whether this script requires database access.
                Defaults to False.
            enable_llm (bool): Whether this script requires LLM access.
                Defaults to False.
            db_connection_getter: Function to get the database connection.
                Defaults to get_connection.
            llm_client (Optional[LLMClientInterface]): LLM client to use.
                Defaults to None.
        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )
        self._db_connection_getter = db_connection_getter
        self._llm_client = llm_client

    def run(self) -> None:
        """
        Abstract method to be implemented by subclasses.

        This method contains the core logic of the analysis script.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def _get_llm_response(self, prompt: str) -> str:
        """
        Helper method to get a response from the LLM.
        """
        if not self._llm_client:
            raise ValueError("LLM client is not initialized.")
        return self._llm_client.generate(prompt)

    def _get_db_connection(self, db_config: Dict[str, Any]) -> DatabaseConnection:
        """
        Helper method to get a database connection.
        """
        return self._db_connection_getter(db_config)


if __name__ == "__main__":

    class MyAnalysisScript(AnalysisScript):
        """
        Example analysis script.
        """

        def __init__(self) -> None:
            """Function __init__."""
            super().__init__(
                name="MyAnalysisScript",
                description="An example analysis script",
                config_section="my_analysis",
                requires_db=True,
                enable_llm=True,
            )

        def run(self) -> None:
            """
            Run the example analysis script.
            """
            self.logger.info("Running MyAnalysisScript")
            # Access configuration values
            example_value = self.get_config_value("utils.example_config", "default_value")
            self.logger.info(f"Example config value: {example_value}")

            # Access database connection
            if self.db_conn:
                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    self.logger.info(f"Database connection test: {result}")
                except Exception as e:
                    self.logger.error(f"Error accessing database: {e}")
                finally:
                    cursor.close()

            # Access LLM client
            if self._llm_client:
                try:
                    response = self._get_llm_response(prompt="Hello, LLM!")
                    self.logger.info(f"LLM response: {response}")
                except Exception as e:
                    self.logger.error(f"Error accessing LLM: {e}")

    # Create and execute the script
    script = MyAnalysisScript()
    script.execute()
