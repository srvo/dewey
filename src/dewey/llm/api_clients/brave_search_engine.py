from typing import Any, Dict, Optional

import requests

from dewey.core.base_script import BaseScript


class BraveSearchEngine(BaseScript):
    """A class for interacting with the Brave search engine."""

    def __init__(self, config: dict[str, Any], name: str = "BraveSearchEngine") -> None:
        """Initializes the BraveSearchEngine.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters.
            name (str): The name of the script instance.

        """
        super().__init__(config=config, name=name)

    def run(self, query: str) -> str | None:
        """Executes a search query using the Brave search engine.

        Args:
            query: The search query.

        Returns:
            The search results as a string, or None if an error occurred.

        Raises:
            Exception: If there is an issue with the search query or API request.

        """
        try:
            api_key = self.get_config_value("brave_search_api_key")
            if not api_key:
                self.logger.error(
                    "Brave Search API key is missing in the configuration."
                )
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
                self.logger.error(
                    f"Brave Search API request failed with status code: {response.status_code}"
                )
                return None

        except Exception as e:
            self.logger.exception(
                f"An error occurred during the Brave Search API request: {e}"
            )
            return None

    def make_request(self, url: str, headers: dict[str, str]) -> requests.Response:
        """Makes an HTTP request to the specified URL.

        Args:
            url: The URL to make the request to.
            headers: The headers to include in the request.

        Returns:
            The response object.

        Raises:
            requests.RequestException: If there is an issue with the request.

        """
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise

    def execute(self) -> None:
        """Executes a search query using the Brave search engine.

        Retrieves the search query from the configuration and calls the run method.
        """
        query = self.get_config_value("query", "Dewey project")
        if query:
            self.logger.info(f"Executing Brave search with query: {query}")
            results = self.run(query)
            if results:
                self.logger.info(f"Brave search results: {results}")
            else:
                self.logger.warning("Brave search failed to return results.")
        else:
            self.logger.warning("No search query found in configuration.")
