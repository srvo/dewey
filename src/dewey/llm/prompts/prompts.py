from typing import Any, Dict

from dewey.core.base_script import BaseScript


class Prompts(BaseScript):
    """A class for managing and generating prompts using LLMs.

    Inherits from:
        BaseScript
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the Prompts class.

        Args:
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config_section="prompts", **kwargs)

    def run(self) -> None:
        """Executes the core logic of the Prompts script.

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

    def generate_prompt(self, template: str, data: dict[str, str]) -> str:
        """Generates a prompt by populating a template with data.

        Args:
            template: The prompt template.
            data: A dictionary containing the data to populate the template.

        Returns:
            The generated prompt.

        Raises:
            ValueError: If a required key is missing in the data.

        """
        try:
            prompt = template.format(**data)
            return prompt
        except KeyError as e:
            self.logger.error(f"Missing key in data: {e}")
            raise ValueError(f"Missing key in data: {e}")
