from dewey.core.base_script import BaseScript


class ContactAgent(BaseScript):
    """
    A class for managing contact-related tasks using LLMs.
    """

    def __init__(self):
        """
        Initializes the ContactAgent, inheriting from BaseScript.
        """
        super().__init__()

    def run(self) -> None:
        """
        Executes the main logic of the ContactAgent.
        """
        self.logger.info("ContactAgent started.")
        config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.info(f"Config value: {config_value}")
        # Add your main logic here
        self.logger.info("ContactAgent finished.")
