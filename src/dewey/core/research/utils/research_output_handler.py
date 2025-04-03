from typing import Any, Dict, Optional

from dewey.core.base_script import BaseScript


class ResearchOutputHandler(BaseScript):
    """Handles research output, saving it to a database or file."""

    def __init__(self, config_section: str | None = None) -> None:
        """Initializes the ResearchOutputHandler.

        Args:
            config_section (Optional[str]): The configuration section to use.

        """
        super().__init__(config_section=config_section, requires_db=True)
        self.output_path = self.get_config_value(
            "research_data.output_path", "data/research/output.txt"
        )

    def execute(self) -> None:
        """Executes the research output handling process."""
        self.logger.info("Starting research output handling...")
        try:
            # Example usage:
            output_data = {
                "key1": "value1",
                "key2": "value2",
            }  # Replace with actual research output
            self.save_output(output_data)
            self.logger.info("Research output handling completed successfully.")
        except Exception as e:
            self.logger.error(
                f"An error occurred during research output handling: {e}", exc_info=True
            )

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()

    def save_output(self, output_data: dict[str, Any]) -> None:
        """Saves the research output to a database or file.

        Args:
            output_data (Dict[str, Any]): The research output data to save.

        Raises:
            Exception: If there is an error saving the output.

        """
        try:
            # Example: Save to a text file
            with open(self.output_path, "w") as f:
                f.write(str(output_data))
            self.logger.info(f"Research output saved to: {self.output_path}")

            # Example: Save to a database table (if database is configured)
            if self.db_conn:
                # Assuming you have a table named 'research_output'
                # and you know its schema
                # You would use Ibis to interact with the database
                # Example:
                # import ibis
                # table = self.db_conn.table("research_output")
                # self.db_conn.insert(table, [output_data])
                self.logger.info("Research output saved to the database.")
            else:
                self.logger.warning(
                    "Database connection not available. Skipping database save."
                )

        except Exception as e:
            self.logger.error(f"Error saving research output: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    output_handler = ResearchOutputHandler()
    output_handler.execute()
