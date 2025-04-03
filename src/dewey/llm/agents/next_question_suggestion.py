from typing import Any, Dict, List

from dewey.core.base_script import BaseScript


class NextQuestionSuggestion(BaseScript):
    """Suggests the next question to ask based on the current conversation.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        """Initializes the NextQuestionSuggestion script.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            **kwargs (Any): Additional keyword arguments.

        """
        super().__init__(config=config, **kwargs)

    def run(self, conversation_history: list[str]) -> str:
        """Executes the next question suggestion logic.

        Args:
            conversation_history: The history of the conversation.

        Returns:
            The suggested next question.

        Raises:
            ValueError: If the prompt template is not found in the configuration.
            Exception: If there is an error during question suggestion.

        """
        try:
            prompt_template = self.get_config_value("next_question_prompt")
            if not prompt_template:
                raise ValueError("Prompt template not found in config.")

            prompt = prompt_template.format(history="\n".join(conversation_history))

            llm_response = self._call_llm(prompt)

            return llm_response.strip()
        except ValueError as ve:
            self.logger.error(f"Configuration error: {ve}")
            raise
        except Exception as e:
            self.logger.exception(f"Error suggesting next question: {e}")
            raise

    def _call_llm(self, prompt: str) -> str:
        """Calls the LLM to generate the next question.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The LLM's response.

        Raises:
            Exception: If the LLM call fails.

        """
        try:
            # Access LLM-related configurations
            model_name = self.get_config_value(
                "llm_model_name", default="gpt-3.5-turbo"
            )
            temperature = self.get_config_value("llm_temperature", default=0.7)

            # Here, instead of directly initializing the LLM, we'd ideally use a
            # pre-configured LLM service or client available within the Dewey
            # environment.  For now, I'll simulate an LLM call.
            self.logger.info(f"Calling LLM: {model_name} with temp: {temperature}")
            llm_response = f"LLM Response to: {prompt}"  # Replace with actual LLM call

            return llm_response
        except Exception as e:
            self.logger.exception(f"LLM call failed: {e}")
            raise
