from typing import Any

from dewey.core.base_script import BaseScript


class CodeGenerator(BaseScript):
    """A script for generating code based on a given prompt.

    This class inherits from BaseScript and implements the run() method
    to execute the code generation logic. It uses the script's logger for
    logging and retrieves configuration values using self.get_config_value().
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the CodeGenerator script.

        Args:
            **kwargs: Keyword arguments passed to the BaseScript constructor.

        """
        super().__init__(**kwargs)

    def execute(self) -> None:
        """Executes the code generation process.

        Retrieves the prompt from the configuration, generates code using
        the LLM, and logs the generated code.

        Raises:
            Exception: If there is an error during code generation.

        """
        try:
            prompt = self.get_config_value("prompt")
            model = self.get_config_value("model", "gpt-3.5-turbo")

            self.logger.info(f"Generating code for prompt: {prompt} using model: {model}")

            if not self.llm_client:
                self.logger.error("LLM client is not initialized.")
                raise ValueError("LLM client is not initialized.  Set enable_llm=True when initializing the script.")

            # Generate code using the LLM client
            response = self.llm_client.generate_text(
                prompt=prompt,
                model=model,
                max_tokens=500,  # Adjust as needed
            )

            generated_code = response.content

            self.logger.info(f"Generated code: {generated_code}")

        except Exception as e:
            self.logger.exception(f"Error during code generation: {e}")
            raise
