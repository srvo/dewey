from typing import Any, Protocol

from dewey.core.base_script import BaseScript


class ConfigHandlerInterface(Protocol):
    """Interface for ConfigHandler."""

    def get_value(self, key: str, default: Any = None) -> Any: ...

    def run(self) -> None: ...


class ConfigHandler(BaseScript, ConfigHandlerInterface):
    """Handles configuration settings for the application.

    This class inherits from BaseScript and provides methods for loading
    and accessing configuration values.
    """

    def __init__(self) -> None:
        """Initializes the ConfigHandler."""
        super().__init__(config_section="config_handler")

    def run(self) -> None:
        """Executes the main logic of the ConfigHandler."""
        self.logger.info("ConfigHandler is running.")

    def get_value(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value by key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if the key is not found.

        """
        return self.get_config_value(key, default)
