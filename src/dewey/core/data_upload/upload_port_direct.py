from dewey.core.base_script import BaseScript


class UploadPortDirect(BaseScript):
    """
    Uploads data directly to a port.

    This class inherits from BaseScript and provides methods for configuring
    and running the data upload process.
    """

    def __init__(self) -> None:
        """
        Initializes the UploadPortDirect class.
        """
        super().__init__(config_section="upload_port_direct")

    def run(self) -> None:
        """
        Runs the data upload process.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If an error occurs during data upload.
        """
        try:
            # Example of accessing configuration values
            port_name = self.get_config_value("port_name", "default_port")
            self.logger.info(f"Starting data upload to port: {port_name}")

            # Add your data upload logic here
            self.logger.info("Data upload process completed.")

        except Exception as e:
            self.logger.exception(f"An error occurred during data upload: {e}")
