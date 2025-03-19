from dewey.core.base_script import BaseScript
from typing import Any, Dict


class OpenRouterClient(BaseScript):
    """A client for interacting with the OpenRouter API."""

    def __init__(self, config_section: str = "openrouter", **kwargs: Any) -> None:
        """Initializes the OpenRouterClient.

        Args:
            config_section (str): The configuration section to use.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(config_section=config_section, **kwargs)

    def run(self) -> None:
        """Executes the main logic of the OpenRouter client.

        This method retrieves the API key from the configuration, logs a message,
        and then could perform other operations with the OpenRouter API.

        Raises:
            ValueError: If the API key is not found in the configuration.

        Returns:
            None
        """
        try:
            api_key = self.get_config_value("openrouter_api_key")
            self.logger.info("OpenRouter client started.")
            # Add your core logic here, e.g., interacting with the OpenRouter API
            self.logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:]}")  # Masking API key in logs
        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            raise

