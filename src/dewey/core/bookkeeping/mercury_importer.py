from dewey.core.base_script import BaseScript


class MercuryImporter(BaseScript):
    """
    Imports data from Mercury.
    """

    def __init__(self):
        """
        Initializes the MercuryImporter.
        """
        super().__init__()

    def run(self) -> None:
        """
        Runs the Mercury importer.
        """
        self.logger.info("Running Mercury importer")
        # Placeholder for mercury import logic
        api_key = self.get_config_value("mercury_api_key")
        if api_key:
            self.logger.info("Mercury API key found.")
        else:
            self.logger.warning("Mercury API key not found in configuration.")
