from dewey.core.base_script import BaseScript


class DatabaseManager(BaseScript):
    """
    Manages database operations using Dewey conventions.

    This class inherits from BaseScript and provides methods for
    interacting with the database, leveraging utilities from
    `dewey.core.db.connection` and `dewey.core.db.utils`.
    """

    def __init__(self) -> None:
        """
        Initializes the DatabaseManager.

        Calls the superclass constructor with the 'database' config section,
        enabling database and LLM functionalities.
        """
        super().__init__(config_section="database", requires_db=True, enable_llm=True)

    def run(self) -> None:
        """
        Executes the main database operations.

        This method demonstrates accessing configuration values,
        establishing a database connection, and performing
        example database operations.

        Raises:
            Exception: If any error occurs during database operations.
        """
        self.logger.info("Starting database operations...")

        try:
            # Accessing a config value
            db_host = self.get_config_value("host", "localhost")
            self.logger.info(f"Database host: {db_host}")

            # Example of using database connection
            if self.db_conn:
                self.logger.info("Successfully connected to the database.")
                # Example of using database utilities (replace with actual logic)
                # For example, if you had a function to create a table:
                # utils.create_table(self.db_conn, "my_table", {"id": "INT", "name": "VARCHAR"})
                # self.logger.info("Created table 'my_table'")
            else:
                self.logger.warning("Database connection not established.")

            self.logger.info("Database operations completed.")

        except Exception as e:
            self.logger.error(
                f"An error occurred during database operations: {e}", exc_info=True
            )
            raise
