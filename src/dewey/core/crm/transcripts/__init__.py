from dewey.core.base_script import BaseScript


class TranscriptsModule(BaseScript):
    """
    A module for managing transcript-related tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for transcript processing scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the TranscriptsModule.

        Args:
        ----
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, **kwargs)
        self.name = "TranscriptsModule"
        self.description = "Manages transcript-related tasks."

    def run(self) -> None:
        """
        Executes the primary logic of the Transcripts module.

        This method retrieves an example configuration value and logs it.
        """
        self.logger.info("Running Transcripts module...")
        # Add your main script logic here
        example_config_value = self.get_config_value("example_config")
        if example_config_value:
            self.logger.info(f"Example config value: {example_config_value}")
        else:
            self.logger.warning("Example config value not found.")

    def get_config_value(self, key: str, default: any = None) -> any:
        """
        Retrieves a configuration value by key.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value, or the default value if the key is not found.

        """
        return super().get_config_value(key, default)
