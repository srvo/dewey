from typing import Any

from dewey.core.base_script import BaseScript


class Prioritization(BaseScript):
    """
    A module for handling prioritization tasks within Dewey's CRM enrichment process.

    This module inherits from BaseScript and provides a standardized
    structure for prioritization scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the Prioritization module.

        Args:
        ----
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, **kwargs, config_section="prioritization")
        self.name = "Prioritization"
        self.description = "Handles prioritization of CRM enrichment tasks."

    def execute(self) -> None:
        """
        Executes the primary logic of the prioritization script.

        This method should be implemented to perform the actual
        prioritization tasks, utilizing configuration values and
        logging as needed.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            Exception: If something goes wrong during prioritization.

        """
        self.logger.info("Starting prioritization process...")

        try:
            # Example of accessing a configuration value
            some_config_value = self.get_config_value(
                "some_config_key", "default_value",
            )
            self.logger.debug("Some config value: %s", str(some_config_value))

            # Add your prioritization logic here
            self.info("Prioritization process completed.")

        except Exception as e:
            self.error(f"Error during prioritization: {e}")
            raise

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.warning("Using deprecated run() method. Update to use execute() instead.")
        self.execute()

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value associated with the key, or the default
            value if the key is not found.

        """
        return super().get_config_value(key, default)
