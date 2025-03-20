from typing import Optional, Callable, Protocol

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm import llm_utils

class LLMClientInterface(Protocol):
    """
    A protocol defining the interface for LLM clients.
    This allows for easier mocking and type checking.
    """
    def generate_response(self, prompt: str) -> Optional[str]:
        ...

class MergeData(BaseScript):
    """
    A class for merging data from different sources.

    This class inherits from BaseScript and provides a standardized
    way to merge data, access configuration, and perform logging.
    """

    def __init__(
        self,
        llm_generate_response: Callable[[LLMClientInterface, str], Optional[str]] = llm_utils.generate_response
    ) -> None:
        """Initializes the MergeData class."""
        super().__init__(
            name="MergeData",
            config_section="merge_data",
            requires_db=True,
            enable_llm=True,
        )
        self._llm_generate_response = llm_generate_response


    def _execute_database_query(self) -> Optional[str]:
        """
        Executes a simple database query.

        Returns:
            The result of the database query, or None if an error occurs.
        """
        try:
            with get_connection().cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.logger.info(f"Database query result: {result}")
                return str(result)  # Ensure a string is returned for consistency
        except Exception as db_error:
            self.logger.error(f"Database error: {db_error}")
            return None


    def _call_llm(self, prompt: str, text: str) -> Optional[str]:
        """
        Calls the LLM to generate a response.

        Args:
            prompt: The prompt to send to the LLM.
            text: The text to include in the prompt.

        Returns:
            The LLM's response, or None if an error occurs.
        """
        try:
            response: Optional[str] = self._llm_generate_response(
                self.llm_client, prompt + text
            )
            if response:
                self.logger.info(f"LLM response: {response}")
                return response
            else:
                self.logger.warning("LLM response was None.")
                return None
        except Exception as llm_error:
            self.logger.error(f"Error during LLM call: {llm_error}")
            return None


    def merge_data(self, input_path: str) -> bool:
        """
        Core logic for merging data.

        Args:
            input_path: The path to the input data.

        Returns:
            True if the data merging was successful, False otherwise.
        """
        self.logger.info(f"Merging data from: {input_path}")

        # Example of using database connection
        if self.db_conn:
            self.logger.info("Database connection is available.")
            self._execute_database_query()
        else:
            self.logger.warning("Database connection is not available.")

        # Example of using LLM
        if self.llm_client:
            self.logger.info("LLM client is available.")
            prompt: str = "Summarize the following text."
            text: str = "This is a sample text for summarization."
            self._call_llm(prompt, text)
        else:
            self.logger.warning("LLM client is not available.")

        # Add your data merging logic here
        self.logger.info("Data merging completed.")
        return True


    def run(self) -> None:
        """
        Executes the data merging process.

        This method retrieves configuration values, performs the data merge,
        and logs the progress and results.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any error occurs during the data merging process.
        """
        self.logger.info("Starting data merging process.")

        try:
            # Accessing configuration values
            input_path: str = self.get_config_value("input_path", "/default/input/path")
            self.logger.info(f"Input path: {input_path}")

            self.merge_data(input_path)

        except Exception as e:
            self.logger.error(f"Error during data merging: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    merge_data = MergeData()
    merge_data.execute()
