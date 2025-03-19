"""Config class to provide access to centralized configuration."""
from typing import Any

from dewey.core.base_script import BaseScript


class CustomScript(BaseScript):
    """
    A custom script inheriting from BaseScript.

    This script demonstrates the Dewey conventions for script structure,
    including configuration access and logging.
    """

    def __init__(self) -> None:
        """Initializes the CustomScript."""
        super().__init__(config_section='custom')

    def run(self) -> None:
        """
        Executes the custom script logic.

        This method demonstrates how to access configuration values and use the
        logger.
        """
        # Example of accessing a configuration value
        example_config_value: Any = self.get_config_value('example_key', 'default_value')
        self.logger.info(f"Example config value: {example_config_value}")

        # Implement script logic here
        self.logger.info("Custom script running")
