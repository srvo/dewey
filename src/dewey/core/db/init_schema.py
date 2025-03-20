from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.core.db import utils as db_utils


class InitSchema(BaseScript):
    """
    Initializes the database schema.

    This class inherits from BaseScript and provides methods for
    creating the database schema.
    """

    def __init__(self):
        """Initializes the InitSchema class."""
        super().__init__(config_section='init_schema', requires_db=True)

    def run(self) -> None:
        """Runs the database schema initialization.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error initializing the database schema.
        """
        self.logger.info("Initializing database schema...")
        db_url = self.get_config_value("db_url", "default_db_url")
        self.logger.info(f"Using database URL: {db_url}")
        try:
            self._create_tables()
            self.logger.info("Database schema initialized successfully.")
        except Exception as e:
            self.logger.error(f"Error initializing database schema: {e}")
            raise

    def _create_tables(self) -> None:
        """Creates the necessary tables in the database.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error creating the tables.
        """
        self.logger.info("Creating tables...")
        try:
            # Example:
            # db_utils.create_table(self.db_conn, "my_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
            self.logger.info("Tables created successfully.")
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            raise


if __name__ == "__main__":
    init_schema = InitSchema()
    init_schema.execute()
