from dewey.core.base_script import BaseScript


class Serper(BaseScript):
    """
    A class for interacting with the Serper API.
    """

    def __init__(self):
        """
        Initializes the Serper class.
        """
        super().__init__(config_section="serper")

    def run(self):
        """
        Executes the main logic of the Serper script.
        """
        api_key = self.get_config_value("api_key")
        self.logger.info(f"Serper script running with API key: {api_key}")
        # Add your Serper API interaction logic here
        pass
