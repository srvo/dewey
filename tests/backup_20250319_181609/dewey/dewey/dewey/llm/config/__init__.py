from dewey.core.base_script import BaseScript
from typing import Any, Dict


class LLMConfig(BaseScript):
    """A class to manage LLM configurations, inheriting from BaseScript."""

    def __init__(self, config_path: str = 'llm_config', **kwargs: Any) -> None:
        """Initializes the LLMConfig with a config path and optional keyword arguments.

        Args:
            config_path: Path to the configuration section. Defaults to 'llm_config'.
            **kwargs: Additional keyword arguments to pass to BaseScript.
        """
        super().__init__(config_section=config_path, **kwargs)

    def run(self) -> Dict[str, Any]:
        """Executes the LLM configuration loading and processing logic.

        Returns:
            A dictionary containing the LLM configuration.

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            llm_model: str = self.get_config_value("llm_model")
            api_key: str = self.get_config_value("api_key")
            temperature: float = self.get_config_value("temperature", default=0.7)

            if not llm_model or not api_key:
                raise ValueError("LLM model and API key must be configured.")

            config: Dict[str, Any] = {
                "llm_model": llm_model,
                "api_key": api_key,
                "temperature": temperature,
            }

            self.logger.info("LLM configuration loaded successfully.")
            return config

        except Exception as e:
            self.logger.exception(f"Error loading LLM configuration: {e}")
            raise
