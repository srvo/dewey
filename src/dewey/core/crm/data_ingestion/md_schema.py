from dewey.core.base_script import BaseScript


class MdSchema(BaseScript):
    """
    A module for managing MD schema within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for schema management, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the MdSchema module."""
        super().__init__(*args, **kwargs)

    def execute(self) -> None:
        """Executes the main logic of the MD Schema module."""
        self.logger.info("Running MD Schema module...")
        # Example of accessing configuration
        example_config_value = self.get_config_value(
            "example_config_key", "default_value",
        )
        self.logger.info(f"Example config value: {example_config_value}")
        # Add your main logic here

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
