from dewey.core.base_script import BaseScript
from typing import Any, Dict


class LLMInterface(BaseScript):
    """
    A class to interface with Large Language Models, adhering to Dewey conventions.
    """

    def __init__(self, config_path: str, script_name: str = "LLMInterface") -> None:
        """
        Initializes the LLMInterface.

        Args:
            config_path (str): Path to the configuration file.
            script_name (str): Name of the script (default: "LLMInterface").
        """
        super().__init__(config_path=config_path, script_name=script_name)

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the core logic of the LLM interface.

        Args:
            input_data (Dict[str, Any]): Input data for the LLM.

        Returns:
            Dict[str, Any]: Output data from the LLM.

        Raises:
            Exception: If an error occurs during LLM processing.
        """
        try:
            # Access configuration values using self.get_config_value()
            model_name = self.get_config_value("llm.model_name")
            api_key = self.get_config_value("llm.api_key")

            self.logger.info(f"Using model: {model_name}")

            # Placeholder for LLM interaction logic
            output_data = {"message": f"Successfully processed data using {model_name}"}

            self.logger.info("LLM processing completed successfully.")
            return output_data

        except Exception as e:
            self.logger.exception(f"An error occurred during LLM processing: {e}")
            raise

