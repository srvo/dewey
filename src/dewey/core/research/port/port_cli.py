import argparse
import sys

from dewey.core.base_script import BaseScript
from dewey.core.db.utils import build_insert_query, create_table, execute_query
from dewey.llm.llm_utils import call_llm


class PortCLI(BaseScript):
    """A command-line interface for interacting with the Port API."""

    def __init__(self) -> None:
        """Initializes the PortCLI script."""
        super().__init__(config_section="port_cli", requires_db=True, enable_llm=True)

    def run(self) -> None:
        """Executes the PortCLI script.

        This method parses command-line arguments, connects to the database,
        fetches data, calls the LLM, and inserts the results into the database.
        """
        args = self.parse_args()

        try:
            # Example usage of database utilities
            table_name = "port_results"
            schema = {"id": "INTEGER", "result": "TEXT"}
            create_table(self.db_conn, table_name, schema)

            # Example usage of LLM utilities
            prompt = "Summarize the following data:"
            data = {"key1": "value1", "key2": "value2"}
            response = call_llm(self.llm_client, prompt + str(data))

            # Insert data into the database
            insert_query = build_insert_query(table_name, ["id", "result"])
            values = [1, response]
            execute_query(self.db_conn, insert_query, values)

            self.logger.info("PortCLI script executed successfully.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}", exc_info=True)
            sys.exit(1)

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up command line arguments.

        Returns:
            An argument parser configured with common options.

        """
        parser = super().setup_argparse()
        # Add any specific arguments for this script here
        return parser


if __name__ == "__main__":
    port_cli = PortCLI()
    port_cli.execute()
