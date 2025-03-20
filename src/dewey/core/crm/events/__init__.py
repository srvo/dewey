from dewey.core.base_script import BaseScript
import logging
from typing import Any

class EventsModule(BaseScript):
    """
    A module for managing event-related tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for event processing scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, name: str = "EventsModule", description: str = "Manages CRM events.") -> None:
        """
        Initializes the EventsModule.
        """
        super().__init__(name=name, description=description)

    def run(self) -> None:
        """
        Executes the primary logic of the EventsModule.
        """
        self.logger.info("Running EventsModule...")
        # Add event processing logic here
        config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.debug(f"Config value for some_config_key: {config_value}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if the key is not found.
        """
        return super().get_config_value(key, default)
