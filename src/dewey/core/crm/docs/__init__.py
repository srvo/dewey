from typing import Any

from dewey.core.base_script import BaseScript


class DocsModule(BaseScript):
    """
    A module for managing documentation tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for documentation-related scripts, including
    configuration loading, logging, and a `run` method to execute
    the script's primary logic.
    """

    def __init__(
        self,
        name: str = "CRM Docs Module",
        description: str = "Manages CRM documentation tasks.",
    ) -> None:
        """
        Initializes the DocsModule.

        Args:
        ----
            name: The name of the module.
            description: A description of the module.

        """
        super().__init__(name=name, description=description, config_section="crm_docs")

    def execute(self) -> None:
        """Executes the primary logic of the documentation module."""
        self.logger.info("Running CRM Docs Module...")

        # Example of accessing configuration values
        example_config_value = self.get_config_value("example_setting", "default_value")
        self.logger.info(f"Example configuration value: {example_config_value}")

        # Add your documentation management logic here
        self.info("CRM Docs Module completed.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
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
            The configuration value, or the default value if the key is not found.

        """
        return super().get_config_value(key, default)
