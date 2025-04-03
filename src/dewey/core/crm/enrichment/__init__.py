"""Module for managing enrichment tasks within Dewey's CRM."""
"""
Dewey CRM Enrichment Module.

This module provides functionality for managing enrichment tasks
within Dewey's CRM.
"""
import logging
from typing import Any

from dewey.core.base_script import BaseScript


class EnrichmentModule(BaseScript):
    """
    A module for managing enrichment tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for enrichment scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, name: str, description: str = "CRM Enrichment Module"):
        """
        Initializes the EnrichmentModule.

        Args:
        ----
            name: The name of the module.
            description: A brief description of the module.

        """
        super().__init__(name=name, description=description)
        self.logger = logging.getLogger(self.name)

    def run(self) -> None:
        """Executes the primary logic of the enrichment module."""
        self.logger.info("Starting enrichment process...")
        # Example of accessing a configuration value
        example_config_value = self.get_config_value("example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")
        # Add your enrichment logic here
        self.logger.info("Enrichment process completed.")

    def execute(self) -> None:
        """Executes the primary logic of the enrichment module."""
        self.logger.info("Starting enrichment process...")
        # Example of accessing a configuration value
        example_config_value = self.get_config_value("example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")
        # Add your enrichment logic here
        self.logger.info("Enrichment process completed.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value associated with the key, or the default value
            if the key is not found.

        """
        return super().get_config_value(key, default)
