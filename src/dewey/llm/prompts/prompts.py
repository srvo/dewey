from dewey.core.base_script import BaseScript
from typing import Any, Dict


class Prompts(BaseScript):
    """
    A class for managing and generating prompts using LLMs.
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

        This method retrieves configuration values, generates prompts,
        and logs relevant information.

        Returns:
            None

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            prompt_template = self.get_config_value("prompt_template")
            model_name = self.get_config_value("model_name")

            self.logger.info(f"Using prompt template: {prompt_template}")
            self.logger.info(f"Using model: {model_name}")

            # Example prompt generation (replace with actual logic)
            prompt = self.generate_prompt(prompt_template, {"task": "summarization"})
            self.logger.info(f"Generated prompt: {prompt}")

        except KeyError as e:
            self.logger.error(f"Missing configuration value: {e}")
            raise ValueError(f"Missing configuration value: {e}")

    def generate_prompt(self, template: str, data: Dict[str, str]) -> str:
        """
        Generates a prompt by populating a template with data.

        Args:
            template (str): The prompt template.
            data (Dict[str, str]): A dictionary containing the data to populate the template.

        Returns:
            str: The generated prompt.
        """
        try:
            prompt = template.format(**data)
            return prompt
        except KeyError as e:
            self.logger.error(f"Missing key in data: {e}")
            raise ValueError(f"Missing key in data: {e}")
