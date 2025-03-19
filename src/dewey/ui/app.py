from dewey.core.base_script import BaseScript
from typing import Any, Dict


class App(BaseScript):
    """
    A sample application script inheriting from BaseScript.
    """

    def __init__(self, config: Dict[str, Any], args: Dict[str, Any]):
        """
        Initializes the App script.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            args (Dict[str, Any]): The arguments dictionary.
        """
        super().__init__(config=config, args=args)

    def run(self) -> None:
        """
        Executes the main logic of the application.

        This example demonstrates accessing configuration values and using the logger.

        Returns:
            None
        """
        try:
            # Access a configuration value
            greeting_target = self.get_config_value("greeting_target", default="World")

            # Log a message
            self.logger.info(f"Hello, {greeting_target}!")

        except Exception as e:
            self.logger.exception("An error occurred during script execution.")
            raise

if __name__ == "__main__":
    # Example usage (replace with your actual config and args)
    config = {"greeting_target": "User"}
    args = {}
    app = App(config=config, args=args)
    app.run()
