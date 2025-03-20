from dewey.core.base_script import BaseScript
from typing import Any

class Config(BaseScript):
    """
    A class to manage configuration settings for Dewey.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self) -> None:
        """
        Initializes the Config object.

        Calls the BaseScript constructor with the 'config' section.
        """
        super().__init__(config_section='config')

    def run(self) -> None:
        """
        Executes the main logic of the Config class.

        This example method demonstrates how to access configuration values
        and use the logger.
        """
        try:
            example_config_value: Any = self.get_config_value('example_key', 'default_value')
            self.logger.info(f"Example config value: {example_config_value}")
        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")

if __name__ == '__main__':
    config = Config()
    config.run()
