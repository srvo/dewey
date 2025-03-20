from typing import Any, Optional

from dewey.core.script import BaseScript


class FormsModule(BaseScript):
    """
    A module for managing form automation tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for form processing scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, config_section: Optional[str] = None) -> None:
        """
        Initializes the FormsModule with optional configuration.

        Args:
            config_section: The section in the dewey.yaml config file
                to use for configuration.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """
        Executes the primary logic of the form automation module.

        This method should be overridden in subclasses to implement
        specific form processing tasks.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If an error occurs during form processing.
        """
        self.logger.info("Forms module started.")
        try:
            # Add your form processing logic here
            # Access configuration values using self.get_config_value("key")
            # Example:
            # api_key = self.get_config_value("api_key")
            # self.logger.info(f"API Key: {api_key}")
            pass
        except Exception as e:
            self.logger.error(f"An error occurred during form processing: {e}")
            raise
        finally:
            self.logger.info("Forms module finished.")

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
