import logging
from typing import Any

from dewey.core.base_script import BaseScript


class LoggingExample(BaseScript):
    """
    A simple example script demonstrating Dewey's logging conventions.

    This script inherits from BaseScript and showcases how to use the
    self.logger for logging messages and self.get_config_value() for
    accessing configuration values.
    """

    def __init__(self, config_section: str = 'logging') -> None:
        """
        Initializes the LoggingExample script.

        Args:
            config_section: The configuration section to use.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """
        Executes the main logic of the script.

        This method demonstrates how to use the logger and access
        configuration values.
        """
        self.logger.info("Starting the LoggingExample script.")

        # Example of accessing a configuration value
        example_config_value: Any = self.get_config_value("example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        self.logger.warning("This is a warning message.")
        self.logger.error("This is an error message.")

        self.logger.info("Finished the LoggingExample script.")


if __name__ == "__main__":
    script = LoggingExample()
    script.execute()
