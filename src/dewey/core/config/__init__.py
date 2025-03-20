from dewey.core.base_script import BaseScript
from typing import Any


class ConfigManager(BaseScript):
    """Manages configuration settings for the application.

    This class inherits from BaseScript and provides methods for loading
    and accessing configuration values.
    """

    def __init__(self, config_section: str = "config_manager") -> None:
        """Initializes the ConfigManager.

        Args:
            config_section: The section in the configuration file to use.
        """
        super().__init__(config_section=config_section)
        self.logger.info("ConfigManager initialized.")

    def run(self) -> None:
        """Runs the configuration manager.

        This method performs setup and initialization tasks, and demonstrates
        accessing a configuration value.
        """
        self.logger.info("ConfigManager running.")
        example_value = self.get_config_value("example_key", "default_value")
        self.logger.info(f"Example configuration value: {example_value}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if the key is not found.
        """
        value = super().get_config_value(key, default)
        self.logger.debug(f"Retrieved config value for key '{key}': {value}")
        return value


if __name__ == "__main__":
    config_manager = ConfigManager()
    config_manager.execute()
