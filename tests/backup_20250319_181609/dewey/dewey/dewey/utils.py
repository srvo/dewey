from typing import Any, Dict

from dewey.core.base_script import BaseScript


class Utils(BaseScript):
    """A utility script demonstrating Dewey conventions."""

    def __init__(self, name: str = "Utils") -> None:
        """Initializes the Utils script.

        Args:
            name: The name of the script.
        """
        super().__init__(config_section='utils', name=name)

    def run(self) -> None:
        """Executes the core logic of the Utils script.

        This example demonstrates accessing configuration values and using the logger.

        Raises:
            Exception: If an error occurs during execution.
        """
        try:
            example_config_value: Any = self.get_config_value("example_config_key")
            self.logger.info(f"Example config value: {example_config_value}")

            self.logger.info("Utility script executed successfully.")

        except Exception as e:
            self.logger.exception(f"An error occurred during execution: {e}")

