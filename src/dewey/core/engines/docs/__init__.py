from typing import Any

from dewey.core.base_script import BaseScript


class DocsEngine(BaseScript):
    """
    A module for managing documentation engine tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for documentation engine scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the DocsEngine module.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, config_section="docs_engine", **kwargs)

    def run(self) -> None:
        """
        Executes the primary logic of the documentation engine module.

        This method should be overridden in subclasses to implement the
        specific documentation engine tasks.
        """
        self.logger.info("Running DocsEngine module.")
        # Example of accessing a configuration value
        example_config_value = self.get_config_value(
            "example_config_key", "default_value"
        )
        self.logger.debug(f"Example config value: {example_config_value}")

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
