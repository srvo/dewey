from dewey.core.base_script import BaseScript
import logging
from typing import Any

class RunEnrichment(BaseScript):
    """
    A module for running enrichment tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for enrichment scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, name: str = "RunEnrichment", description: str = "Runs enrichment tasks.") -> None:
        """
        Initializes the RunEnrichment module.

        Args:
            name (str): The name of the module.
            description (str): A description of the module.
        """
        super().__init__(name=name, description=description)

    def run(self) -> None:
        """
        Executes the primary logic of the enrichment script.
        """
        self.logger.info("Starting enrichment process...")
        # Access configuration values using self.get_config_value()
        api_key = self.get_config_value("enrichment.api_key")
        if api_key:
            self.logger.info("API key found in configuration.")
            # Perform enrichment tasks here
        else:
            self.logger.warning("API key not found in configuration. Enrichment tasks will not be executed.")
        self.logger.info("Enrichment process completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by key.

        Args:
            key (str): The key of the configuration value to retrieve.
            default (Any, optional): The default value to return if the key is not found. Defaults to None.

        Returns:
            Any: The configuration value, or the default value if the key is not found.
        """
        return super().get_config_value(key, default)
