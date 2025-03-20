from typing import Optional

from dewey.core.base_script import BaseScript
from dewey.llm.llm_utils import call_llm


class MyUtils(BaseScript):
    """
    A comprehensive class for utility functions, including database connections,
    LLM integrations, and configuration management.
    """

    def __init__(self, config_section: Optional[str] = "utils") -> None:
        """Initialize MyUtils with configuration and optional database/LLM.

        Args:
            config_section (Optional[str]): Section in dewey.yaml to load for
                this script. Defaults to "utils".
        """
        super().__init__(
            name=self.__class__.__name__,
            description="Utility functions for Dewey project",
            config_section=config_section,
            requires_db=True,
            enable_llm=True,
        )
        self.logger.info(f"Initialized {self.name}")

    def run(self) -> None:
        """
        Run the utility functions. This is the main entry point for the script.
        """
        try:
            self.logger.info("Starting utility functions...")
            # Example usage of config, database, and LLM
            example_config_value = self.get_config_value("example_config", "default_value")
            self.logger.info(f"Example config value: {example_config_value}")

            # Example database operation
            if self.db_conn:
                self.logger.info("Executing example database operation...")
                # Example: Fetching data (replace with your actual query)
                # Assuming you have a table named 'example_table'
                try:
                    with self.db_conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        result = cursor.fetchone()
                        self.logger.info(f"Database query result: {result}")
                except Exception as e:
                    self.logger.error(f"Error executing database query: {e}")
            else:
                self.logger.warning("Database connection is not available.")

            # Example LLM call
            if self.llm_client:
                self.logger.info("Making example LLM call...")
                try:
                    prompt = "Write a short poem about utility functions."
                    response = call_llm(prompt, llm_client=self.llm_client)
                    self.logger.info(f"LLM response: {response}")
                except Exception as e:
                    self.logger.error(f"Error calling LLM: {e}")
            else:
                self.logger.warning("LLM client is not available.")

            self.logger.info("Utility functions completed.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}", exc_info=True)

    def example_utility_function(self, input_data: str) -> str:
        """
        An example utility function that processes input data.

        Args:
            input_data (str): The input data to process.

        Returns:
            str: The processed output data.
        """
        self.logger.info(f"Processing input data: {input_data}")
        output_data = f"Processed: {input_data}"
        self.logger.info(f"Output data: {output_data}")
        return output_data


if __name__ == "__main__":
    script = MyUtils()
    script.execute()
