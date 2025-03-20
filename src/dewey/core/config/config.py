from typing import Any, Optional

from dewey.core.base_script import BaseScript


class Config(BaseScript):
    """
    A class to manage configuration settings for Dewey.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self, name: str = "Config", config_section: str = "core") -> None:
        """
        Initializes the Config object.

        Calls the BaseScript constructor with the 'config' section.
        """
        super().__init__(name=name, config_section=config_section)

    def run(self) -> None:
        """
        Executes the main logic of the Config class.

        Demonstrates how to access configuration values and use the logger.
        """
        try:
            example_config_value: Any = self.get_config_value(
                "example_key", "default_value"
            )
            self.logger.info(f"Example config value: {example_config_value}")

            # Example of accessing a nested configuration value
            log_level: str = self.get_config_value("logging.level", "INFO")
            self.logger.info(f"Current log level: {log_level}")

        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")


if __name__ == "__main__":
    config = Config()
    config.execute()
