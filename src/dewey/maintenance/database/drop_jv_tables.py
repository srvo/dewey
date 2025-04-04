from dewey.core.base_script import BaseScript


class DropJVTables(BaseScript):
    """
    A script to drop JV-related tables from the database.

    This script inherits from BaseScript and provides a standardized
    structure for database maintenance scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def run(self) -> None:
        """Executes the script's primary logic to drop JV tables."""
        self.logger.info("Starting the process to drop JV tables.")

        # Example of accessing a configuration value
        db_name = self.get_config_value("database_name", "default_db")
        self.logger.info(f"Using database: {db_name}")

        # Add your database dropping logic here
        # For example:
        # self.drop_table("jv_table_1")
        # self.drop_table("jv_table_2")

        self.logger.info("Finished dropping JV tables.")

    def drop_table(self, table_name: str) -> None:
        """
        Drops a specified table from the database.

        Args:
        ----
            table_name: The name of the table to drop.

        """
        self.logger.info(f"Dropping table: {table_name}")
        # Add actual database dropping code here, using a database connection
        # obtained from configuration or elsewhere.

    def execute(self) -> None:
        """
        Executes the script's primary logic to drop JV tables.

        This method retrieves a list of table names from the configuration
        and attempts to drop each table from the database.
        """
        self.logger.info("Starting the process to drop JV tables.")

        table_names = self.get_config_value("tables_to_drop", [])

        if not table_names:
            self.logger.info("No tables specified to drop.")
            return

        with self.db_connection() as conn:
            with conn.cursor() as cursor:
                for table_name in table_names:
                    try:
                        self.logger.info(f"Dropping table: {table_name}")
                        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                        conn.commit()
                        self.logger.info(f"Successfully dropped table: {table_name}")
                    except Exception as e:
                        self.logger.error(f"Error dropping table {table_name}: {e}")
                        conn.rollback()

        self.logger.info("Finished dropping JV tables.")
