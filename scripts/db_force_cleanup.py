from typing import Any

from dewey.core.base_script import BaseScript


class ForceCleanup(BaseScript):
    """A module for forcing database cleanup tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for database cleanup scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the ForceCleanup module."""
        super().__init__(*args, **kwargs)

    def execute(self) -> None:
        """Executes the database cleanup logic.

        This method should contain the core logic for performing
        the database cleanup tasks.
        """
        self.logger.info("Starting database cleanup...")
        # Add your database cleanup logic here
        config_value = self.get_config_value("cleanup_setting", "default_value")
        self.logger.info(f"Using cleanup setting: {config_value}")
        self.logger.info("Database cleanup completed.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()


if __name__ == "__main__":
    # Example usage (for testing purposes)
    script = ForceCleanup()
    script.run()
