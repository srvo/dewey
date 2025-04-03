from dewey.core.base_script import BaseScript
from dewey.core.db.connection import (
    DatabaseConnection,
    get_connection,
    get_motherduck_connection,
)


class PriorityModule(BaseScript):
    """A module for managing priority-related tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for priority scripts, including configuration loading,
    logging, and a `run` method to execute the script's primary logic.
    """

    def __init__(
        self, name: str = "PriorityModule", description: str = "Priority Module"
    ):
        """Initializes the PriorityModule.

        Args:
            name: The name of the module.
            description: A brief description of the module.

        """
        super().__init__(name=name, description=description, config_section="priority")

    def run(self) -> None:
        """Executes the primary logic of the priority module.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error during the execution of the priority module.

        """
        self.logger.info("Running priority module...")

        try:
            # Example of accessing a configuration value
            some_config_value = self.get_config_value(
                "some_config_key", "default_value"
            )
            self.logger.info(f"Some config value: {some_config_value}")

            # Example of database connection
            if self.db_conn:
                self.logger.info("Database connection is available.")
                # Example of using the database connection
                # with self.db_conn.cursor() as cursor:
                #     cursor.execute("SELECT 1")
                #     result = cursor.fetchone()
                #     self.logger.info(f"Database query result: {result}")
            else:
                self.logger.warning("Database connection is not available.")

            # Add your priority logic here
            self.logger.info("Priority logic completed.")

        except Exception as e:
            self.logger.error(f"Error in priority module: {e}", exc_info=True)
            raise
