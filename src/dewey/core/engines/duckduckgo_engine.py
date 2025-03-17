
# Refactored from: duckduckgo_engine
# Date: 2025-03-16T16:19:09.546146
# Refactor Version: 1.0
```python
"""
DuckDuckGo Search Engine
======================

Provides search functionality using the DuckDuckGo API with rate limiting.
"""

import logging
from typing import Any, Dict, List, Optional

from duckduckgo_search import DDGS
from ratelimit import limits, sleep_and_retry

from .base import SearchEngine


class DuckDuckGoEngine(SearchEngine):
    """
    Search engine implementation using DuckDuckGo.

    Provides rate-limited access to DuckDuckGo's search API with
    automatic retries and error handling.

    Attributes:
        ddgs: DuckDuckGo search client.
        calls_per_minute: Rate limit for API calls.
        logger: Logger instance.
    """

    def __init__(self) -> None:
        """Initialize the DuckDuckGo search engine."""
        self.ddgs = DDGS()
        self.calls_per_minute = 15
        self.logger = logging.getLogger(self.__class__.__name__)

    @sleep_and_retry
    @limits(calls=15, period=60)
    def search(
        self, query: str, max_results: int = 10, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Execute a search query on DuckDuckGo.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.
            **kwargs: Additional search parameters.
                - region: Search region (default: 'wt-wt').
                - safesearch: Safe search setting (default: 'moderate').

        Returns:
            List of dictionaries containing search results with fields:
            - title: Result title.
            - link: Result URL.
            - snippet: Result text snippet.
            - source: Always 'ddg'.
            - raw: Raw API response.
        """
        results: List[Dict[str, Any]] = []
        try:
            search_results = self._execute_search(query, max_results, **kwargs)
            results = self._process_search_results(search_results)
            self.logger.info(f"Processed {len(results)} results successfully")
            return results
        except Exception:
            self.logger.error("Failed to process search results", exc_info=True)
            return []

    def _execute_search(
        self, query: str, max_results: int, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Execute the search query using the DuckDuckGo API.

        Args:
            query: The search query.
            max_results: The maximum number of results to return.
            **kwargs: Additional keyword arguments to pass to the API.

        Returns:
            A list of raw search results from the API.
        """
        search_results = list(
            self.ddgs.text(
                query,
                region=kwargs.get("region", "wt-wt"),
                safesearch=kwargs.get("safesearch", "moderate"),
                max_results=max_results,
            )
        )
        self.logger.info(f"Found {len(search_results)} raw results")
        return search_results

    def _process_search_results(
        self, search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process raw search results into a standardized format.

        Args:
            search_results: A list of raw search results.

        Returns:
            A list of processed search results.
        """
        results: List[Dict[str, Any]] = []
        for r in search_results:
            try:
                link: Optional[str] = None
                if isinstance(r, dict):
                    for field in ["link", "url", "href"]:
                        link = r.get(field)
                        if link:
                            break

                results.append(
                    {
                        "title": r.get("title", "No title"),
                        "link": link or "No link",
                        "snippet": r.get("body", r.get("snippet", "No snippet")),
                        "source": "ddg",
                        "raw": r,
                    }
                )
            except AttributeError:
                self.logger.error(f"Unexpected result format: {r}", exc_info=True)
                continue
        return results
```
