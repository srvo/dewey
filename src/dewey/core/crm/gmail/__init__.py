from dewey.core.base_script import BaseScript
import logging
from typing import Any, Optional


class GmailModule(BaseScript):
    """
    A module for managing Gmail-related tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for Gmail processing scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the GmailModule."""
        super().__init__(*args, **kwargs)
        self.name = "GmailModule"
        self.description = "Manages Gmail-related tasks."

    def run(self) -> None:
        """
        Executes the primary logic of the Gmail module.
        """
        self.logger.info("Gmail module started.")
        # Add your Gmail logic here
        api_key: Optional[str] = self.get_config_value("gmail_api_key")
        if api_key:
            self.logger.debug("Gmail API key found in config.")
        else:
            self.logger.warning("Gmail API key not found in config.")
        self.logger.info("Gmail module finished.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value associated with the key, or the default value
            if the key is not found.
        """
        return super().get_config_value(key, default)
