from dewey.core.base_script import BaseScript
from typing import Any

class CLI(BaseScript):
    """
    A command-line interface class that inherits from BaseScript.

    This class provides a basic structure for creating command-line
    interfaces within the Dewey framework. It leverages BaseScript
    for configuration, logging, and other common functionalities.
    """

    def __init__(self) -> None:
        """
        Initializes the CLI class.

        Calls the BaseScript constructor with the 'cli' configuration section.
        """
        super().__init__(config_section='cli')

    def run(self) -> None:
        """
        Executes the main logic of the CLI.

        This method should be overridden in subclasses to implement
        the specific functionality of the command-line interface.
        """
        self.logger.info("CLI is running...")
        # Example of accessing a configuration value
        example_config_value = self.get_config_value('example_config_key', 'default_value')
        self.logger.info(f"Example config value: {example_config_value}")

if __name__ == '__main__':
    cli = CLI()
    cli.run()
