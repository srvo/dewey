from typing import Any, Dict, Optional

from dewey.core.script import BaseScript


class DocsModule(BaseScript):
    """
    A module for managing documentation tasks within Dewey's automation scripts.

    This module inherits from BaseScript and provides a standardized
    structure for documentation-related scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the DocsModule with optional configuration.

        Args:
            config (Optional[Dict[str, Any]]): A dictionary containing
                configuration parameters. Defaults to None.
        """
        super().__init__(config)

    def run(self) -> None:
        """
        Executes the primary logic of the documentation module.

        This method should be overridden in subclasses to implement
        specific documentation tasks.
        """
        self.logger.info("Running the Docs module...")
        # Add your documentation logic here

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key (str): The key of the configuration value to retrieve.
            default (Any): The default value to return if the key is not found.

        Returns:
            Any: The configuration value associated with the key, or the
            default value if the key is not found.
        """
        return super().get_config_value(key, default)
