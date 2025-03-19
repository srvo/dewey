from dewey.core.base_script import BaseScript
from typing import Any, Dict, Optional


class BraveSearchEngine(BaseScript):
    """
    A class for interacting with the Brave search engine.
    """

    def __init__(self, config: Dict[str, Any], name: str = "BraveSearchEngine") -> None:
        """
        Initializes the BraveSearchEngine.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters.
            name (str): The name of the script instance.
        """
        super().__init__(config=config, name=name)

    def run(self, query: str) -> Optional[str]:
        """
        Executes a search query using the Brave search engine.

        Args:
            query (str): The search query.

        Returns:
            Optional[str]: The search results, or None if an error occurred.

        Raises:
            Exception: If there is an issue with the search query or API request.
        """
        try:
            api_key = self.get_config_value("brave_search_api_key")
            if not api_key:
                self.logger.error("Brave Search API key is missing in the configuration.")
                return None

            # Construct the search URL
            search_url = f"https://api.search.brave.com/res/v1/web/search?q={query}"

            # Make the API request
            headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
            response = self.make_request(url=search_url, headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                results = response.json()
                return str(results)  # Returning the results as a string
            else:
                self.logger.error(f"Brave Search API request failed with status code: {response.status_code}")
                return None

        except Exception as e:
            self.logger.exception(f"An error occurred during the Brave Search API request: {e}")
            return None

    def make_request(self, url: str, headers: Dict[str, str]) -> Any:
        """
        Makes an HTTP request to the specified URL.

        Args:
            url (str): The URL to make the request to.
            headers (Dict[str, str]): The headers to include in the request.

        Returns:
            Any: The response object.

        Raises:
            Exception: If there is an issue with the request.
        """
        pass
