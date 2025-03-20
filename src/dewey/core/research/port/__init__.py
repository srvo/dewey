from dewey.core.base_script import BaseScript
import logging
from typing import Any, Dict


class PortModule(BaseScript):
    """
    Base class for port modules within Dewey.

    This class provides a standardized structure for port scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(self, name: str, description: str = "Port Module"):
        """Initializes the PortModule."""
        super().__init__(name, description)

    def run(self) -> None:
        """
        Executes the primary logic of the port module.
        """
        self.logger.info("Running the port module...")
        # Add your implementation here

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
