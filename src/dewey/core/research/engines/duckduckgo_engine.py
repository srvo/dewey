from dewey.core.base_script import BaseScript
from duckduckgo_search import ddg


class DuckDuckGoEngine(BaseScript):
    """A class to interact with the DuckDuckGo search engine."""

    def __init__(self):
        """Initializes the DuckDuckGoEngine with configurations."""
        super().__init__(config_section="research_engines.duckduckgo")

    def execute(self, query: str, max_results: int = 5) -> list[dict]:
        """Executes a search query using the DuckDuckGo search engine.

        Args:
            query: The search query string.
            max_results: The maximum number of search results to return.

        Returns:
            A list of dictionaries, where each dictionary represents a search result.
            Each dictionary contains the keys 'title', 'href', and 'body'.

        """
        self.logger.info(f"Executing DuckDuckGo search for query: {query}")
        try:
            results = ddg(query, max_results=max_results)
            self.logger.info(f"Successfully retrieved {len(results)} results.")
            return results
        except Exception as e:
            self.logger.error(f"Error during DuckDuckGo search: {e}")
            return []
