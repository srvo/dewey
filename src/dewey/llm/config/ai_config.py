from typing import Any, Dict

from dewey.core.base_script import BaseScript


class AIConfig(BaseScript):
    """A class to manage AI configurations, inheriting from BaseScript."""

    def __init__(self, script_name: str, config: dict[str, Any]) -> None:
        """Initializes the AIConfig script.

        Args:
            script_name: The name of the script.
            config: The configuration dictionary.

        """
        super().__init__(script_name=script_name, config_section="ai_config")
        self.config_data = config  # Store the config data

    def run(self) -> None:
        """Executes the AI configuration logic.

        This method demonstrates accessing configuration values and logging
        messages using the BaseScript's utilities.

        Raises:
            ValueError: If a required configuration value is missing or invalid.

        """
        try:
            # Example of accessing a configuration value
            model_name = self.get_config_value("model_name", str)
            self.logger.info(f"Using model: {model_name}")

            # Example of accessing another configuration value
            temperature = self.get_config_value("temperature", float)
            self.logger.info(f"Temperature setting: {temperature}")

        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            raise

        self.logger.info("AI Configuration script completed.")


if __name__ == "__main__":
    # Example usage (replace with your actual configuration)
    config_data = {"model_name": "GPT-4", "temperature": 0.7}
    ai_config = AIConfig(script_name="ai_config_script", config=config_data)
    ai_config.run()
