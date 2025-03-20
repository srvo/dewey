from typing import Any

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection


class PortDatabase(BaseScript):
    """
    Manages the port database operations.

    This class inherits from BaseScript and provides methods for
    interacting with the port database.
    """

    def __init__(self) -> None:
        """Initializes the PortDatabase class."""
        super().__init__(config_section="port_database")

    def run(self) -> None:
        """
        Runs the main logic of the PortDatabase.

        This method retrieves the database URL from the configuration,
        establishes a database connection, and performs database operations.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error during database operations.
        """
        self.logger.info("Starting Port Database operations.")

        try:
            # Accessing the database URL from the configuration
            database_url = self.get_config_value("database.url", "default_url")
            self.logger.info(f"Database URL: {database_url}")

            # Establishing a database connection
            with get_connection(self.config.get("database", {})) as db_conn:
                if isinstance(db_conn, DatabaseConnection):
                    self.logger.info("Successfully connected to the database.")
                    # Example database operation (replace with your actual logic)
                    # For example, you might use Ibis to interact with the database
                    # and perform queries or schema operations.
                    # Example:
                    # table = db_conn.con.table("your_table")
                    # result = table.limit(10).execute()
                    # self.logger.info(f"Example query result: {result}")
                else:
                    self.logger.warning(
                        "Database connection is not an instance of DatabaseConnection."
                    )

            self.logger.info("Port Database operations completed.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}", exc_info=True)
            raise
