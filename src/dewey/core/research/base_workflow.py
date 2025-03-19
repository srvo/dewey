from dewey.core.base_script import BaseScript
from typing import Any, Dict

class BaseWorkflow(BaseScript):
    """
    Base class for research workflows, inheriting from BaseScript.
    """

    def __init__(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """
        Initializes the BaseWorkflow.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config=config, **kwargs)

    def run(self) -> None:
        """
        Executes the core logic of the workflow.  Must be implemented by subclasses.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def get_config_value(self, key: str) -> Any:
        """
        Retrieves a configuration value by key.

        Args:
            key (str): The key of the configuration value to retrieve.

        Returns:
            Any: The value associated with the key.
        """
        return self.config.get(key)

    def log_info(self, message: str) -> None:
        """
        Logs an informational message.

        Args:
            message (str): The message to log.
        """
        self.logger.info(message)

    def log_error(self, message: str) -> None:
        """
        Logs an error message.

        Args:
            message (str): The message to log.
        """
        self.logger.error(message)
