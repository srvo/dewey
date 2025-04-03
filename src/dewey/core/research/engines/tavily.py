from dewey.core.base_script import BaseScript


class Tavily(BaseScript):
    """A class for interacting with the Tavily API.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self):
        """Initializes the Tavily class.

        Calls the superclass constructor to initialize the BaseScript.
        """
        super().__init__(config_section="tavily")

    def execute(self) -> None:
        """Executes the main logic of the Tavily script.

        This method is the entry point for the script and should be
        implemented to perform the desired actions.
        """
        api_key = self.get_config_value("api_key")
        self.logger.info(f"Tavily API Key: {api_key}")
        # Implement Tavily API interaction here
        pass

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()
