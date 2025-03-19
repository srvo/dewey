from dewey.core.base_script import BaseScript
from typing import Any, Dict


class ClientAdvocateAgent(BaseScript):
    """
    A client advocate agent that interacts with LLMs to provide support and guidance.
    """

    def __init__(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """
        Initializes the ClientAdvocateAgent.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config=config, **kwargs)

    def run(self) -> None:
        """
        Executes the core logic of the client advocate agent.

        This method retrieves configuration values, interacts with LLMs,
        and performs necessary actions based on the agent's objectives.

        Raises:
            Exception: If there is an error during the agent's execution.

        Returns:
            None
        """
        try:
            agent_name = self.get_config_value("agent_name", default="Client Advocate")
            self.logger.info(f"Starting {agent_name}...")

            # Example of accessing a config value
            llm_model = self.get_config_value("llm_model", default="gpt-3.5-turbo")
            self.logger.info(f"Using LLM model: {llm_model}")

            # Add your core logic here, using self.logger for logging
            self.logger.info("Performing client advocacy tasks...")

        except Exception as e:
            self.logger.exception(f"An error occurred during execution: {e}")
