from dewey.core.base_script import BaseScript


class MotherDuck(BaseScript):
    """A class for interacting with MotherDuck."""

    def __init__(self):
        """Initializes the MotherDuck class."""
        super().__init__(config_section="motherduck")

    def execute(self) -> None:
        """Executes the main logic of the MotherDuck script."""
        self.logger.info("Running MotherDuck script")
        # Example of accessing configuration values
        api_token = self.get_config_value("api_token")
        self.logger.debug(f"API Token: {api_token}")

        # Add your MotherDuck interaction logic here
        self.logger.info("MotherDuck script completed")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()
