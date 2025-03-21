from typing import Any, Dict

from dewey.core.base_script import BaseScript


class Prompts(BaseScript):
    """A class for managing and executing prompt-related tasks.

    Inherits from:
        BaseScript
    """

    def __init__(self, config_section: str = 'prompts', **kwargs: Any) -> None:
        """Initializes the Prompts class.

        Args:
            config_section (str): The configuration section to use. Defaults to 'prompts'.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config_section=config_section, **kwargs)

    def run(self) -> None:
        """Executes the core logic of the Prompts script.

        This method retrieves a prompt and an API key from the configuration,
        and logs them.

        Raises:
            ValueError: If the 'prompt' configuration value is not found.
            ValueError: If the 'api_key' configuration value is not found.

        Returns:
            None
        """
        try:
            prompt: str = self.get_config_value("prompt")
            self.info(f"Retrieved prompt: {prompt}")
        except ValueError as e:
            self.error(f"Error retrieving prompt: {e}")
            raise

        try:
            api_key: str = self.get_config_value("api_key")
            self.info(f"Retrieved API key: {api_key}")
        except ValueError as e:
            self.error(f"Error retrieving API key: {e}")
            raise
