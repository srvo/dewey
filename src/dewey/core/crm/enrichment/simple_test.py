from dewey.core.base_script import BaseScript


class SimpleTest(BaseScript):
    """
    A simple test module for Dewey.

    This module demonstrates the basic structure of a Dewey script,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the SimpleTest module.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.name = "SimpleTest"
        self.description = "A simple test script for Dewey."

    def run(self) -> None:
        """
        Executes the main logic of the SimpleTest module.
        """
        self.logger.info("Starting SimpleTest module...")

        # Accessing configuration values
        example_config_value = self.get_config_value("example_config_key", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        self.logger.info("SimpleTest module finished.")
