from dewey.core.base_script import BaseScript
from dewey.llm import llm_utils


class MergeData(BaseScript):
    """
    A class for merging data from different sources.

    This class inherits from BaseScript and provides a standardized
    way to merge data, access configuration, and perform logging.
    """

    def __init__(self) -> None:
        """Initializes the MergeData class."""
        super().__init__(
            name="MergeData",
            config_section="merge_data",
            requires_db=True,
            enable_llm=True,
        )

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
            input_path = self.get_config_value("input_path", "/default/input/path")
            self.logger.info(f"Input path: {input_path}")

            # Example of using database connection
            if self.db_conn:
                self.logger.info("Database connection is available.")
                # Example database operation (replace with actual logic)
                # with self.db_conn.cursor() as cursor:
                #     cursor.execute("SELECT 1")
                #     result = cursor.fetchone()
                #     self.logger.info(f"Database query result: {result}")
            else:
                self.logger.warning("Database connection is not available.")

            # Example of using LLM
            if self.llm_client:
                self.logger.info("LLM client is available.")
                # Example LLM call (replace with actual logic)
                prompt = "Summarize the following text."
                text = "This is a sample text for summarization."
                try:
                    response = llm_utils.generate_response(
                        self.llm_client, prompt + text
                    )
                    self.logger.info(f"LLM response: {response}")
                except Exception as e:
                    self.logger.error(f"Error during LLM call: {e}")
            else:
                self.logger.warning("LLM client is not available.")

            # Add your data merging logic here
            self.logger.info("Data merging completed.")

        except Exception as e:
            self.logger.error(f"Error during data merging: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    merge_data = MergeData()
    merge_data.execute()
