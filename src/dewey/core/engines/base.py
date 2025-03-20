from dewey.core.base_script import BaseScript
from typing import Any

class BaseEngine(BaseScript):
    """Base class for all engines."""

    def __init__(self, config_section: str = 'base_engine') -> None:
        """Initializes the BaseEngine.

        Args:
            config_section: The configuration section to use.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Runs the engine.

        This method should be overridden by subclasses to implement the
        engine's functionality.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Gets a configuration value.

        Args:
            key: The key of the configuration value.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if the key is not found.
        """
        return super().get_config_value(key, default)

    def info(self, message: str) -> None:
        """Logs an info message.

        Args:
            message: The message to log.
        """
        self.logger.info(message)

    def error(self, message: str) -> None:
        """Logs an error message.

        Args:
            message: The message to log.
        """
        self.logger.error(message)
