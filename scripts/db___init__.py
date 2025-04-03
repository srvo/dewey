from typing import Any

from dewey.core.base_script import BaseScript


class DatabaseModule(BaseScript):
    """
    A module for managing database maintenance tasks
    within Dewey.
    """
    """
    This module inherits from BaseScript and provides a
    standardized structure for database maintenance scripts,
    including configuration loading, logging, and a `run` method
    to execute the script's primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the DatabaseModule."""
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """Executes the database maintenance tasks.

        This method contains the primary logic for the database maintenance
        script. It can access configuration values using
        `self.get_config_value()` and log messages using `self.logger`.
        """
        self.logger.info("Starting database maintenance tasks.")

        # Example of accessing a configuration value
        database_url = self.get_config_value("database_url")
        if database_url:
            self.logger.info(f"Using database URL: {database_url}")
        else:
            self.logger.warning("Database URL not configured.")

        # Add your database maintenance logic here
        self.logger.info("Database maintenance tasks completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value associated with the given key.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value associated with the key, or the default
            value if the key is not found.

        """
        return super().get_config_value(key, default)
