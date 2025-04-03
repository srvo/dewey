th
"""Data handler for database operations.

This module provides a utility class for handling data operations with the database.
"""

from contextlib import contextmanager
from typing import Any, Dict

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection


class DataHandler(BaseScript):
    """Class for handling data operations with the database.

    This class extends BaseScript to provide methods for data management
    and database operations.
    """

    def __init__(self, name: str) -> None:
        """Initialize the DataHandler with a name.

        Args:
            name: A descriptive name for this data handler

        Raises:
            TypeError: If name is not a string

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a string.")

        self.name = name
        super().__init__(config_section="db")

    def __repr__(self) -> str:
        """Return string representation of the DataHandler instance."""
        return f"DataHandler(name='{self.name}')"

    def execute(self) -> None:
        """Executes the data handler script.

        This method performs database operations using the configuration
        from the config file.
        """
        self.logger.info("Running DataHandler script...")

        try:
            db_config = self.get_config_value("database")
            if not db_config:
                self.logger.error("Database configuration not found.")
                return

            with self._get_db_connection(db_config) as conn:
                # Perform database operations here
                self._process_data(conn)

            self.logger.info("DataHandler script completed.")

        except Exception as e:
            self.logger.error(f"Error during database operation: {e}")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()

    @contextmanager
    def _get_db_connection(self, db_config: dict[str, Any]):
        """Context manager for getting a database connection.

        Args:
            db_config: Database configuration dictionary

        Yields:
            A database connection to use in a with statement

        """
        conn = get_connection(db_config)
        try:
            yield conn
        finally:
            conn.close()

    def _process_data(self, conn: Any) -> None:
        """Process data using the database connection.

        This is a placeholder method that should be overridden by subclasses.

        Args:
            conn: Database connection object

        """
        # Default implementation does nothing
        pass
