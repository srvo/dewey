from dewey.core.base_script import BaseScript
import logging


class ApiManager(BaseScript):
    """
    Manages API interactions, providing a base class for API-related scripts.

    This class inherits from BaseScript and provides standardized access to
    configuration and logging.
    """

    def __init__(self, logger: logging.Logger = None):
        """Initializes the ApiManager."""
        super().__init__(config_section='api_manager')
        if logger:
            self.logger = logger

    def run(self) -> None:
        """
        Executes the main logic of the API manager.

        This method should be overridden by subclasses to implement specific
        API-related tasks.
        """
        self.logger.info("ApiManager started.")
        # Add your API logic here
        self.logger.info("ApiManager finished.")
