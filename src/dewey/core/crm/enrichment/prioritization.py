from dewey.core.base_script import BaseScript
from typing import Any

class Prioritization(BaseScript):
    """
    A module for handling prioritization tasks within Dewey's CRM enrichment process.

    This module inherits from BaseScript and provides a standardized
    structure for prioritization scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initializes the Prioritization module.
        """
        super().__init__(*args, **kwargs)
        self.name = "Prioritization"
        self.description = "Handles prioritization of CRM enrichment tasks."

    def run(self) -> None:
        """
        Executes the primary logic of the prioritization script.

        This method should be implemented to perform the actual
        prioritization tasks, utilizing configuration values and
        logging as needed.
        """
        self.logger.info("Starting prioritization process...")

        # Example of accessing a configuration value
        some_config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.debug(f"Some config value: {some_config_value}")

        # Add your prioritization logic here
        self.logger.info("Prioritization process completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value associated with the key, or the default
            value if the key is not found.
        """
        return super().get_config_value(key, default)
