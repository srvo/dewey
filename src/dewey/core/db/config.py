from dewey.core.base_script import BaseScript
from dewey.core.db.connection import (
    DatabaseConnection,
    get_connection,
    get_motherduck_connection,
)


class Config(BaseScript):
    """
    Manages database configuration.

    This class inherits from BaseScript and provides methods for
    configuring the database.
    """

    def __init__(self) -> None:
        """Initializes the Config class."""
        super().__init__(config_section="db_config", requires_db=True)

    def run(self) -> None:
        """
        Runs the database configuration.

        Demonstrates accessing configuration values and using database utilities.
        """
        self.logger.info("Running database configuration...")

        # Accessing configuration values
        db_host = self.get_config_value("host", "localhost")
        self.logger.info(f"Database host: {db_host}")

        # Example of using database connection utilities
        try:
            # Get a MotherDuck connection
            motherduck_connection: DatabaseConnection = get_motherduck_connection(
                self.config.get("test_config", {})
            )
            self.logger.info("Successfully obtained MotherDuck connection.")

            # Example query (replace with your actual query)
            # Assuming you have a table named 'my_table'
            # with a column named 'my_column'
            query = "SELECT COUNT(*) FROM my_table"
            result = motherduck_connection.execute(query)
            self.logger.info(f"Query result: {result}")

            # Get a generic database connection
            generic_connection: DatabaseConnection = get_connection(
                self.config.get("test_config", {})
            )
            self.logger.info("Successfully obtained generic database connection.")

            # Example schema operation (replace with your actual schema operation)
            # Assuming you want to create a table named 'new_table'
            # with columns 'id' (INTEGER) and 'name' (VARCHAR)
            create_table_query = """
                CREATE TABLE IF NOT EXISTS new_table (
                    id INTEGER,
                    name VARCHAR
                )
            """
            generic_connection.execute(create_table_query)
            self.logger.info("Successfully created table 'new_table'.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise
