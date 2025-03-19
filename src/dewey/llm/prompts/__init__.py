from dewey.core.base_script import BaseScript
from typing import Any, Dict

class Prompts(BaseScript):
    """
    A class for managing and executing prompt-related tasks.
    """

    def __init__(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """
        Initializes the Prompts class.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config=config, **kwargs)

    def run(self) -> None:
        """
        Executes the core logic of the Prompts script.

        This method retrieves a prompt from the configuration, logs it,
        and then retrieves and logs an API key.

        Raises:
            ValueError: If the 'prompt' configuration value is not found.
            ValueError: If the 'api_key' configuration value is not found.

        Returns:
            None
        """
        try:
            prompt = self.get_config_value("prompt")
            self.logger.info(f"Retrieved prompt: {prompt}")
        except ValueError as e:
            self.logger.error(f"Error retrieving prompt: {e}")
            raise

        try:
            api_key = self.get_config_value("api_key")
            self.logger.info(f"Retrieved API key: {api_key}")
        except ValueError as e:
            self.logger.error(f"Error retrieving API key: {e}")
            raise
