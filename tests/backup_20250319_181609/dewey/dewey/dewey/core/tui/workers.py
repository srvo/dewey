from dewey.core.base_script import BaseScript
import logging
from typing import Any

class Workers(BaseScript):
    """
    A class for managing worker threads.

    Inherits from BaseScript and provides methods for starting, stopping,
    and monitoring worker threads.
    """

    def __init__(self):
        """
        Initializes the Workers class.
        """
        super().__init__(config_section='workers')

    def run(self) -> None:
        """
        Main method to execute the worker's functionality.
        """
        self.logger.info("Worker started.")
        # Add worker logic here
        config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.info(f"Config value: {config_value}")

    def some_method(self, arg: str) -> None:
        """
        Example method demonstrating logging and config access.

        Args:
            arg: A string argument.
        """
        self.logger.debug(f"Some method called with arg: {arg}")
        some_other_config = self.get_config_value("some_other_config", 123)
        self.logger.info(f"Some other config: {some_other_config}")
