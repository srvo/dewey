from dewey.core.base_script import BaseScript

class APIClient(BaseScript):
    """
    Base class for API clients, inheriting from BaseScript.
    """
    def __init__(self, config_path: str, profile: str = "default") -> None:
        """
        Initializes the APIClient.

        Args:
            config_path (str): Path to the configuration file.
            profile (str, optional): Profile to use from the configuration file. Defaults to "default".
        """
        super().__init__(config_path=config_path, profile=profile)

    def run(self) -> None:
        """
        Executes the main logic of the API client.

        This method should be overridden by subclasses to implement
        the specific API client logic.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def get_api_key(self) -> str:
        """
        Retrieves the API key from the configuration.

        Returns:
            str: The API key.

        Raises:
            ValueError: If the API key is not found in the configuration.
        """
        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("API key not found in configuration.")
            raise ValueError("API key not found in configuration.")
        return api_key

    def make_api_request(self, endpoint: str, data: dict) -> dict:
        """
        Makes a request to the API endpoint.

        Args:
            endpoint (str): The API endpoint to call.
            data (dict): The data to send in the request.

        Returns:
            dict: The JSON response from the API.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("Subclasses must implement the make_api_request method.")
