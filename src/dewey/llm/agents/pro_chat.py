from typing import Any, Dict
from dewey.core.base_script import BaseScript


class ProChat(BaseScript):
    """A class for professional chat interactions, inheriting from BaseScript."""

    def __init__(self, config_section: str = 'pro_chat', **kwargs: Any) -> None:
        """Initializes the ProChat agent.

        Args:
            config_section (str): Configuration section name. Defaults to 'pro_chat'.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config_section=config_section, **kwargs)

    def run(self) -> None:
        """Executes the core logic of the ProChat agent.

        This method retrieves configuration values, initializes necessary components,
        and performs the main operations of the chat agent.

        Raises:
            Exception: If there is an error during the execution.
        """
        try:
            # Access configuration values using self.get_config_value()
            model_name = self.get_config_value("model_name", default="gpt-3.5-turbo")
            temperature = self.get_config_value("temperature", default=0.7)

            self.logger.info(f"Starting ProChat with model: {model_name} and temperature: {temperature}")

            # Simulate chat interactions
            self.logger.info("Simulating chat interactions...")
            self.logger.info("Interaction 1: User says hello.")
            self.logger.info("Interaction 2: Agent responds professionally.")

            self.logger.info("ProChat execution completed successfully.")

        except Exception as e:
            self.logger.exception(f"An error occurred during ProChat execution: {e}")
            raise


if __name__ == "__main__":
    # Example usage (replace with actual configuration)
    config: Dict[str, Any] = {
        "model_name": "gpt-4",
        "temperature": 0.8
    }
    agent = ProChat()
    agent.run()
