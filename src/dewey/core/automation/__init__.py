from typing import Any, Dict

from dewey.core.base_script import BaseScript


class AutomationModule(BaseScript):
    """
    Base class for automation modules within Dewey.

    This class provides a standardized structure for automation scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(self, config_section: str = 'automation'):
        """
        Initializes the AutomationModule.

        Args:
            config_section: The configuration section to use for this module.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """
        Executes the main logic of the automation module.

        This method should be overridden by subclasses to implement
        the specific automation tasks.
        """
        self.logger.info("Automation module started.")
        # Add your automation logic here
        config_value = self.get_config_value("example_config_key", "default_value")
        self.logger.info(f"Example config value: {config_value}")
        self.logger.info("Automation module finished.")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value for the module.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default value if not found.
        """
        return super().get_config_value(key, default)


if __name__ == '__main__':
    # Example usage:
    automation_module = AutomationModule()
    automation_module.run()
