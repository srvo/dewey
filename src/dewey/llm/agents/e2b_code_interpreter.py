from dewey.core.base_script import BaseScript


class E2BCodeInterpreter(BaseScript):
    """
    A class for interacting with the E2B code interpreter.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(
        self,
        config_section: str = "E2BCodeInterpreter",
        name: str = "E2BCodeInterpreter",
    ) -> None:
        """
        Initializes the E2BCodeInterpreter.

        Args:
        ----
            config_section (str): The configuration section to use.
            name (str): The name of the script.

        """
        super().__init__(config_section=config_section, name=name)

    def execute(self) -> None:
        """
        Executes the core logic of the E2B code interpreter.

        Retrieves configuration values, initializes necessary components,
        and performs the main operations of the code interpreter.

        Raises
        ------
            Exception: If an error occurs during execution.

        """
        try:
            # Example of accessing configuration values
            api_key = self.get_config_value("e2b_api_key")
            self.logger.info(f"E2B API Key: {api_key}")

            # Add your core logic here, using self.logger for logging
            self.logger.info("Starting E2B code interpretation...")

            # Placeholder for actual code interpretation logic
            result = self.interpret_code("print('Hello, world!')")
            self.logger.info(f"Code interpretation result: {result}")

            self.logger.info("E2B code interpretation completed.")

        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")
            raise

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()

    def interpret_code(self, code: str) -> str:
        """
        Interprets the given code using the E2B code interpreter.

        Args:
        ----
            code (str): The code to interpret.

        Returns:
        -------
            str: The result of the code interpretation.

        """
        # Placeholder for actual code interpretation logic
        self.logger.info(f"Interpreting code: {code}")
        return f"Result of interpreting: {code}"
