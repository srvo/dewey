from dewey.core.base_script import BaseScript
import logging
from typing import Any

class CrmModule(BaseScript):
    """
    A module for managing CRM-related tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for CRM scripts, including configuration loading, logging,
    and a `run` method to execute the script's primary logic.
    """

    def __init__(self, name: str = "CRM Module", description: str = "Manages CRM tasks.") -> None:
        """
        Initializes the CRM module.
        """
        super().__init__(name, description)

    def run(self) -> None:
        """
        Executes the primary logic of the CRM module.
        """
        self.logger.info("Starting CRM module...")

        # Example of accessing a configuration value
        api_key = self.get_config_value("crm.api_key", default="default_api_key")
        self.logger.debug(f"CRM API Key: {api_key}")

        # Add your CRM logic here
        self.logger.info("CRM module completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if the key is not found.
        """
        return super().get_config_value(key, default)
