import httpx
from dewey.core.base_script import BaseScript


class SearxNG(BaseScript):
    """A class for interacting with a SearxNG instance."""

    def __init__(self) -> None:
        """Initializes the SearxNG instance."""
        super().__init__(config_section="searxng")

    def run(self) -> None:
        """Executes the main logic of the SearxNG script.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error during the SearxNG script execution.

        """
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.logger.info("Starting SearxNG script")
        try:
            # Example of accessing configuration values
            api_url = self.get_config_value("api_url", "http://localhost:8080")
            self.logger.info(f"SearxNG API URL: {api_url}")

            # Add your SearxNG interaction logic here
            self.logger.info("SearxNG script completed")
        except Exception as e:
            self.logger.error(f"Error during SearxNG script execution: {e}")
            raise

    def execute(self) -> None:
        """Executes a search using the SearxNG API and logs the results.

        Args:
            None

        Returns:
            None

        Raises:
            httpx.RequestError: If the request to the SearxNG API fails.
            Exception: If there is an error during the search execution.

        """
        self.logger.info("Starting SearxNG search execution")
        try:
            api_url = self.get_config_value("api_url", "http://localhost:8080")
            search_query = self.get_config_value("search_query", "Dewey Investments")
            self.logger.info(f"Searching SearxNG for: {search_query}")

            search_url = f"{api_url}/search?q={search_query}"
            try:
                response = httpx.get(search_url, timeout=30)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            except httpx.RequestError as e:
                self.logger.error(f"Request failed: {e}")
                raise

            results = response.json()
            self.logger.info(f"SearxNG search results: {results}")

            self.logger.info("SearxNG search execution completed")
        except Exception as e:
            self.logger.error(f"Error during SearxNG search execution: {e}")
            raise
