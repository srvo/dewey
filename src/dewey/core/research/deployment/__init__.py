from dewey.core.base_script import BaseScript
from typing import Any

class DeploymentModule(BaseScript):
    """
    Base class for deployment modules within Dewey.

    This class provides a standardized structure for deployment scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the DeploymentModule."""
        super().__init__(*args, **kwargs)
        self.name = "DeploymentModule"
        self.description = "Base class for deployment modules."

    def run(self) -> None:
        """
        Executes the deployment logic.

        This method should be overridden by subclasses to implement the
        specific deployment steps.
        """
        self.logger.info("Deployment module started.")
        # Add deployment logic here
        config_value = self.get_config_value("example_config_key", "default_value")
        self.logger.info(f"Example config value: {config_value}")
        self.logger.info("Deployment module finished.")
