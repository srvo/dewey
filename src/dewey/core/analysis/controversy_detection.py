from typing import Any, Optional

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection, get_motherduck_connection
from dewey.core.db import utils as db_utils
from dewey.llm import llm_utils


class ControversyDetection(BaseScript):
    """
    A class for detecting controversy in text.

    Inherits from BaseScript and provides methods for initializing
    and running controversy detection.
    """

    def __init__(self, config_section: Optional[str] = None) -> None:
        """
        Initializes the ControversyDetection class.

        Calls the superclass constructor to initialize the base script.

        Args:
            config_section (Optional[str], optional): Section in the config file
                to use for configuration. Defaults to None.
        """
        super().__init__(
            config_section=config_section,
            name="ControversyDetection",
            requires_db=True,  # Assuming controversy detection might use a database
            enable_llm=True,  # Assuming controversy detection might use an LLM
        )

    def run(self, data: Any = None) -> Any:
        """
        Executes the controversy detection process.

        Args:
            data (Any, optional): Input data for controversy detection.
                Defaults to None.

        Returns:
            Any: The result of the controversy detection process.
        """
        self.logger.info("Starting controversy detection...")

        # Example of accessing configuration values
        some_config_value = self.get_config_value("utils.example_config", "default_value")
        self.logger.debug(f"Some config value: {some_config_value}")

        # Example of using database connection
        try:
            # Example query (replace with your actual query)
            query = "SELECT * FROM example_table;"
            result = self.db_conn.execute(query)
            self.logger.debug(f"Database query result: {result}")
        except Exception as e:
            self.logger.error(f"Error executing database query: {e}")

        # Example of using LLM
        try:
            prompt = "Is this text controversial? " + str(data)
            llm_response = llm_utils.generate_response(self.llm_client, prompt)
            self.logger.debug(f"LLM response: {llm_response}")
            result = llm_response  # Use LLM response as result
        except Exception as e:
            self.logger.error(f"Error using LLM: {e}")
            result = None

        self.logger.info("Controversy detection complete.")
        return result


if __name__ == "__main__":
    # Example usage
    detector = ControversyDetection()
    detector.execute()
