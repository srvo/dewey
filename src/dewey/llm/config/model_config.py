from typing import Any, Dict

from dewey.core.base_script import BaseScript


class ModelConfig(BaseScript):
    """A script for managing LLM model configurations.

    Inherits from BaseScript for standardized configuration, logging,
    and other utilities.
    """

    def __init__(self, config: dict[str, Any], dry_run: bool = False) -> None:
        """Initializes the ModelConfig script.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            dry_run (bool, optional): If True, the script will not perform any
                actual operations. Defaults to False.

        """
        super().__init__(config=config, dry_run=dry_run)

    def run(self) -> None:
        """Executes the model configuration logic.

        This method retrieves model parameters from the configuration and
        logs them. In a real implementation, this could involve loading
        models, validating configurations, or updating model settings.

        Raises:
            ValueError: If a required configuration value is missing.

        Returns:
            None

        """
        try:
            model_name = self.get_config_value("model_name")
            model_version = self.get_config_value("model_version")

            self.logger.info(
                f"Configuring model: {model_name}, version: {model_version}"
            )

            # Example of accessing a nested configuration
            llm_params = self.get_config_value("llm_params", default={})
            self.logger.info(f"LLM Parameters: {llm_params}")

            # Add more model configuration logic here

        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            raise

        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")
            raise
