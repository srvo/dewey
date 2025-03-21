from typing import Any, Dict

from dewey.core.base_script import BaseScript


class ChatAgent(BaseScript):
    """A chat agent that interacts with the user.

    This class inherits from BaseScript and implements the Dewey conventions
    for logging, configuration, and script execution.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the ChatAgent.

        Args:
            **kwargs: Keyword arguments passed to the BaseScript constructor.
        """
        super().__init__(**kwargs)

    def run(self) -> None:
        """Executes the core logic of the chat agent.

        This method retrieves configuration values, interacts with the user,
        and logs the interaction.

        Raises:
            Exception: If there is an error during the chat interaction.

        Returns:
            None
        """
        try:
            agent_name = self.get_config_value("agent_name", "ChatAgent")
            self.logger.info(f"Starting {agent_name}...")

            user_input = input("Enter your message: ")
            self.logger.info(f"User input: {user_input}")

            response = self._process_input(user_input)
            print(response)  # Keep print for user output

            self.logger.info("Chat interaction complete.")

        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")
            raise

    def _process_input(self, user_input: str) -> str:
        """Processes the user input and generates a response.

        Args:
            user_input: The input message from the user.

        Returns:
            The response generated by the agent.
        """
        # Placeholder for actual LLM or other processing logic
        response = f"You said: {user_input}"
        return response
