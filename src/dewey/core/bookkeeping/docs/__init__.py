from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
import logging
from typing import Any, Dict


class DocsModule(BaseScript):
    """
    A module for managing documentation tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for documentation-related scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, name: str, description: str = "Documentation Module"):
        """
        Initializes the DocsModule.

        Args:
            name (str): The name of the module.
            description (str, optional): A brief description of the module.
                Defaults to "Documentation Module".
        """
        super().__init__(name=name, description=description, config_section="docs")

    def run(self) -> None:
        """
        Executes the primary logic of the documentation module.

        This method should be overridden in subclasses to implement
        specific documentation tasks.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If something goes wrong during the documentation task.
        """
        self.logger.info("Running the Docs module...")
        try:
            # Example of accessing a configuration value
            example_config_value = self.get_config_value("docs_setting", "default_value")
            self.logger.info(f"Example config value: {example_config_value}")

            # Add your documentation logic here
            self.logger.info("Documentation tasks completed.")

        except Exception as e:
            self.logger.error(f"An error occurred during documentation: {e}", exc_info=True)
            raise

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key (str): The key of the configuration value to retrieve.
            default (Any, optional): The default value to return if the key
                is not found in the configuration. Defaults to None.

        Returns:
            Any: The configuration value associated with the key, or the
                default value if the key is not found.
        """
        return super().get_config_value(key, default)
