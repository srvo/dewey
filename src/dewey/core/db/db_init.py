from dewey.core.base_script import BaseScript


class DbInit(BaseScript):
    """
    Initializes the database.

    This class inherits from BaseScript and provides methods for
    initializing the database.
    """

    def __init__(self) -> None:
        """Initializes the DbInit class."""
        super().__init__(config_section="db_init", requires_db=True)

    def run(self) -> None:
        """Runs the database initialization process.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error during database initialization.
        """
        self.logger.info("Starting database initialization...")

        try:
            # Access database host from configuration
            db_host = self.get_config_value("core.database.host", "localhost")
            self.logger.info(f"Database host: {db_host}")

            # Example database operation (replace with actual initialization logic)
            with self.db_conn.cursor() as cursor:
                cursor.execute("SELECT 1;")  # Example query
                result = cursor.fetchone()
                self.logger.info(f"Database check result: {result}")

            self.logger.info("Database initialization complete.")

        except Exception as e:
            self.logger.error(f"Error during database initialization: {e}")
            raise


if __name__ == "__main__":
    db_init = DbInit()
    db_init.execute()
