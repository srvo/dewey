from dewey.core.base_script import BaseScript

class Utils(BaseScript):
    """
    A collection of utility functions for the Dewey project.

    This class inherits from BaseScript and provides access to
    configuration, logging, and other common functionalities.
    """

    def __init__(self) -> None:
        """
        Initializes the Utils class.
        """
        super().__init__(config_section='utils')

    def run(self) -> None:
        """
        Executes the main logic of the utility module.
        """
        self.logger.info("Running utils module...")
        # Add your utility functions here
        config_value = self.get_config_value("example_config_key", "default_value")
        self.logger.info(f"Example config value: {config_value}")
