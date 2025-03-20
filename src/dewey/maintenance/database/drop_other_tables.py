from dewey.core.base_script import BaseScript


class DropOtherTables(BaseScript):
    """
    A script to drop all tables except the ones specified in the configuration.

    This script inherits from BaseScript and provides a standardized
    structure for database maintenance, including configuration loading,
    logging, and a `run` method to execute the script's primary logic.
    """

    def run(self) -> None:
        """
        Executes the script to drop all tables except the specified ones.
        """
        self.logger.info("Starting the process to drop other tables.")

        # Example of accessing a configuration value
        tables_to_keep = self.get_config_value("tables_to_keep", [])

        if not isinstance(tables_to_keep, list):
            self.logger.error(
                "The 'tables_to_keep' configuration value must be a list."
            )
            return

        self.logger.info(f"Tables to keep: {tables_to_keep}")

        # Add your database dropping logic here, using self.logger for logging
        # and self.get_config_value() to access configuration values.

        self.logger.info("Finished the process to drop other tables.")
