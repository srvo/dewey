from typing import Any

from dewey.core.base_script import BaseScript


class CleanupOtherFiles(BaseScript):
    """A script for cleaning up other files in the database.

    This script inherits from BaseScript and provides a standardized
    structure for database cleanup, including configuration loading,
    logging, and a `run` method to execute the script's primary logic.
    """

    def run(self) -> None:
        """Executes the database cleanup process."""
        self.logger.info("Starting database cleanup process.")

        # Example of accessing a configuration value
        config_value: Any = self.get_config_value("some_config_key", "default_value")
        self.logger.debug(f"Config value for some_config_key: {config_value}")

        # Add your database cleanup logic here
        self.logger.info("Database cleanup process completed.")


if __name__ == "__main__":
    cleanup_script = CleanupOtherFiles()
    cleanup_script.run()
