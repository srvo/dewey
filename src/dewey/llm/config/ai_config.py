from dewey.core.base_script import BaseScript
from typing import Any, Dict


class AIConfig(BaseScript):
    """
    A class to manage AI configurations, inheriting from BaseScript.
    """

    def __init__(self, script_name: str, config: Dict[str, Any]):
        """
        Initializes the AIConfig script.

        Args:
            script_name (str): The name of the script.
            config (Dict[str, Any]): The configuration dictionary.
        """
        super().__init__(script_name=script_name, config=config)

    def run(self) -> None:
        """
        Executes the AI configuration logic.

        This method demonstrates accessing configuration values and logging messages
        using the BaseScript's utilities.

        Returns:
            None

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
