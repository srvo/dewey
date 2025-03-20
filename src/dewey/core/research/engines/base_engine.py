from dewey.core.base_script import BaseScript


class BaseEngine(BaseScript):
    """Base class for all engines.

    This class provides a foundation for building engines within the Dewey
    project, offering standardized configuration, logging, and database/LLM
    integration.
    """

    def __init__(self, config_section: str = "engines") -> None:
        """Initializes the BaseEngine.

        Args:
            config_section: The section in the dewey.yaml configuration file
                            containing the engine's specific settings. Defaults to "engines".
        """
        super().__init__(config_section=config_section, requires_db=False, enable_llm=False)

    def run(self) -> None:
        """Executes the main logic of the engine.

        This method should be overridden by subclasses to implement
        the specific functionality of the engine.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def info(self, message: str) -> None:
        """Logs an info message using the configured logger.

        Args:
            message: The message to log.
        """
        self.logger.info(message)
