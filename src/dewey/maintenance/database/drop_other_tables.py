from dewey.core.base_script import BaseScript


class DropOtherTables(BaseScript):
    """
    A script to drop all tables except the ones specified in the configuration.

    This script inherits from BaseScript and provides a standardized
    structure for database maintenance, including configuration loading,
    logging, and a `run` method to execute the script's primary logic.
    """

    def run(self) -> None:
        """Executes the script to drop all tables except the specified ones."""
        self.logger.info("Starting the process to drop other tables.")

        # Example of accessing a configuration value
        tables_to_keep = self.get_config_value("tables_to_keep", [])

        if not isinstance(tables_to_keep, list):
            self.logger.error(
                "The 'tables_to_keep' configuration value must be a list.",
            )
            return

        self.logger.info(f"Tables to keep: {tables_to_keep}")

        # Add your database dropping logic here, using self.logger for logging
        # and self.get_config_value() to access configuration values.

        self.logger.info("Finished the process to drop other tables.")

    def execute(self) -> None:
        """Executes the script to drop all tables except the specified ones."""
        self.logger.info("Starting the process to drop other tables.")

        tables_to_keep = self.get_config_value("tables_to_keep", [])

        if not isinstance(tables_to_keep, list):
            self.logger.error(
                "The 'tables_to_keep' configuration value must be a list.",
            )
            return

        self.logger.info(f"Tables to keep: {tables_to_keep}")

        try:
            with self.db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';",
                    )
                    all_tables = [row[0] for row in cursor.fetchall()]
                    self.logger.debug(f"All tables in database: {all_tables}")

                    tables_to_drop = [
                        table for table in all_tables if table not in tables_to_keep
                    ]
                    self.logger.info(f"Tables to drop: {tables_to_drop}")

                    for table in tables_to_drop:
                        try:
                            self.logger.info(f"Dropping table: {table}")
                            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                            conn.commit()
                            self.logger.info(f"Dropped table: {table}")
                        except Exception as e:
                            self.logger.error(f"Error dropping table {table}: {e}")
                            conn.rollback()

        except Exception as e:
            self.logger.error(f"Error during database operations: {e}")

        self.logger.info("Finished the process to drop other tables.")
