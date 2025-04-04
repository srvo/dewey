import argparse
import sys

from dewey.core.base_script import BaseScript
from dewey.core.db.utils import build_insert_query
from dewey.llm.litellm_utils import quick_completion


class PortCLI(BaseScript):
    """A command-line interface for interacting with the Port API."""

    def __init__(self) -> None:
        """Initializes the PortCLI script."""
        super().__init__(config_section="port_cli", requires_db=True, enable_llm=True)

    def execute(self) -> None:
        """
        Executes the PortCLI script.

        This method parses command-line arguments, connects to the database,
        fetches data, calls the LLM, and inserts the results into the database.
        """
        args = self.parse_args()

        if not self.db_conn:
            self.logger.error("Database connection required but not available.")
            sys.exit(1)

        try:
            table_name = "port_results"
            # Define schema as SQL
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                result TEXT
            );
            """
            # Use db_conn.execute
            with self.db_connection() as conn:
                conn.execute(create_table_sql)

                # Use quick_completion and self.llm_client
                prompt = "Summarize the following data:"
                data = {"key1": "value1", "key2": "value2"}
                response = quick_completion(
                    prompt + str(data), llm_client=self.llm_client,
                )

                # Insert data into the database using build_insert_query and db_conn.execute
                # Assume build_insert_query returns (query_string, values_tuple)
                insert_data = {"id": 1, "result": response}
                insert_query, values = build_insert_query(table_name, insert_data)
                conn.execute(insert_query, values)
                conn.commit()

            self.logger.info("PortCLI script executed successfully.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}", exc_info=True)
            sys.exit(1)

    def run(self) -> None:
        """Legacy method for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()

    def setup_argparse(self) -> argparse.ArgumentParser:
        """
        Set up command line arguments.

        Returns
        -------
            An argument parser configured with common options.

        """
        parser = super().setup_argparse()
        # Add any specific arguments for this script here
        return parser


if __name__ == "__main__":
    port_cli = PortCLI()
    port_cli.execute()
