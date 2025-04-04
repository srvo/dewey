from dewey.core.base_script import BaseScript


class ApiManager(BaseScript):
    """
    Manages API interactions, providing a base class for API-related scripts.

    This class inherits from BaseScript and provides standardized access to
    configuration and logging.
    """

    def __init__(self):
        """Initializes the ApiManager."""
        super().__init__(config_section="api_manager")
        # Logger is already set up by the BaseScript class

    def run(self) -> None:
        """
        Executes the main logic of the API manager.

        This method should be overridden by subclasses to implement specific
        API-related tasks.
        """
        self.logger.info("ApiManager started.")
        # Add your API logic here
        self.logger.info("ApiManager finished.")

    def execute(self) -> None:
        """
        Executes the main logic of the API manager.

        This method logs the start and finish of the API manager's execution.
        Subclasses should override this method to implement specific
        API-related tasks.
        """
        self.logger.info("ApiManager execute started.")
        # Add your API logic here
        self.logger.info("ApiManager execute finished.")
