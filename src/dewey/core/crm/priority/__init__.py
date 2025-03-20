from dewey.core.base_script import BaseScript


class PriorityModule(BaseScript):
    """
    A module for managing priority-related tasks within Dewey's CRM.

    This module inherits from BaseScript and provides a standardized
    structure for priority scripts, including configuration loading,
    logging, and a `run` method to execute the script's primary logic.
    """

    def __init__(self, name: str, description: str = "Priority Module"):
        """
        Initializes the PriorityModule.

        Args:
            name: The name of the module.
            description: A brief description of the module.
        """
        super().__init__(name=name, description=description)

    def run(self) -> None:
        """
        Executes the primary logic of the priority module.
        """
        self.logger.info("Running priority module...")

        # Example of accessing a configuration value
        some_config_value = self.get_config_value("some_config_key", "default_value")
        self.logger.info(f"Some config value: {some_config_value}")

        # Add your priority logic here
        self.logger.info("Priority logic completed.")
