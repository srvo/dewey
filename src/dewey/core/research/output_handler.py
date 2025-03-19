from dewey.core.base_script import BaseScript
from typing import Any, Dict


class OutputHandler(BaseScript):
    """
    Handles the output of research tasks, ensuring proper logging and configuration.
    """

    def __init__(self, config_path: str, **kwargs: Any) -> None:
        """
        Initializes the OutputHandler.

        Args:
            config_path (str): Path to the configuration file.
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(config_path, **kwargs)

    def run(self) -> None:
        """
        Executes the core logic of the output handler.

        This method retrieves configuration values, processes data,
        and logs relevant information.

        Raises:
            ValueError: If a required configuration value is missing.
        """
        try:
            output_path = self.get_config_value("output_path")
            if not output_path:
                raise ValueError("Output path must be specified in the config.")

            # Simulate processing data and writing output
            output_data = {"status": "success", "message": "Data processed successfully."}
            self.write_output(output_path, output_data)

        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")

    def write_output(self, output_path: str, data: Dict[str, Any]) -> None:
        """
        Writes the output data to the specified path.

        Args:
            output_path (str): The path to write the output data.
            data (Dict[str, Any]): The data to write.
        """
        try:
            # In a real implementation, this would write to a file or database.
            self.logger.info(f"Writing output to: {output_path}")
            self.logger.debug(f"Output data: {data}")
            # Placeholder for actual writing logic
        except Exception as e:
            self.logger.error(f"Failed to write output to {output_path}: {e}")
