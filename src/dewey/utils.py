from dewey.core.base_script import BaseScript
from typing import Any, Dict


class Utils(BaseScript):
    """
    A utility script demonstrating Dewey conventions.
    """

    def __init__(self, config: Dict[str, Any], name: str = "Utils") -> None:
        """
        Initializes the Utils script.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            name (str): The name of the script.
        """
        super().__init__(config, name)

    def run(self) -> None:
        """
        Executes the core logic of the Utils script.

        This example demonstrates accessing configuration values and using the logger.
        """
        try:
            example_config_value = self.get_config_value("example_config_key")
            self.logger.info(f"Example config value: {example_config_value}")

            self.logger.info("Utility script executed successfully.")

        except Exception as e:
            self.logger.exception(f"An error occurred during execution: {e}")
