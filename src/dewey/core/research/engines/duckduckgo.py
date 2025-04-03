from dewey.core.base_script import BaseScript
from duckduckgo_search import ddg


class DuckDuckGo(BaseScript):
    """A class for interacting with the DuckDuckGo search engine.

    Inherits from BaseScript and provides methods for performing searches
    and retrieving results.
    """

    def __init__(self):
        """Initializes the DuckDuckGo search engine."""
        super().__init__(config_section="duckduckgo")

    def run(self):
        """Executes the main logic of the DuckDuckGo script."""
        query = self.get_config_value("query", "default_query")
        self.logger.info(f"Searching DuckDuckGo for: {query}")
        results = self.search(query)
        self.logger.info(f"Results: {results}")

    def search(self, query: str) -> str:
        """Performs a search on DuckDuckGo and returns the results.

        Args:
            query: The search query.

        Returns:
            The search results as a string.

        """
        # Implement your DuckDuckGo search logic here
        # This is just a placeholder
        return f"DuckDuckGo search results for: {query}"

    def execute(self) -> None:
        """Executes the DuckDuckGo search and logs the results."""
        query = self.get_config_value("query", "default_query")
        max_results = self.get_config_value("max_results", 5)

        self.logger.info(f"Executing DuckDuckGo search for: {query}")

        try:
            results = ddg(query, max_results=max_results)
            self.logger.info(f"DuckDuckGo search results: {results}")
        except Exception as e:
            self.logger.error(f"Error during DuckDuckGo search: {e}")
