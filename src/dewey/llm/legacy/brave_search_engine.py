
# Refactored from: brave_search_engine
# Date: 2025-03-16T16:19:10.598078
# Refactor Version: 1.0
# Formatting failed: LLM generation failed: Gemini API error: Could not acquire rate limit slot for gemini-2.0-flash after 3 attempts

"""Brave Search Engine.
================

Provides functionality to perform web and local searches using the Brave Search API.
"""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .base import BaseEngine


class BraveSearchEngine(BaseEngine):
    """Research engine for performing searches using Brave Search API.

    Provides functionality to:
    - Execute web searches
    - Perform local business searches
    - Handle rate limiting and retries
    - Process and validate responses
    """

    BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        """Initialize the Brave Search engine.

        Args:
        ----
            api_key: Brave Search API key. If None, will try to get from environment
            max_retries: Maximum number of retry attempts for failed requests

        """
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.session = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        import os

        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            msg = (
                "Brave Search API key not found. Please set BRAVE_API_KEY environment variable "
                "or pass api_key to constructor."
            )
            raise ValueError(
                msg,
            )
        return api_key

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def _close_session(self) -> None:
        """Close aiohttp session if it exists."""
        if self.session:
            await self.session.close()
            self.session = None

    async def process(self) -> dict[str, Any]:
        """Process method required by BaseEngine.
        Not typically used for this engine as it's primarily accessed via search methods.
        """
        return {"status": "Brave Search engine ready"}

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the Brave Search API.

        Args:
        ----
            endpoint: API endpoint to call
            params: Query parameters
            headers: Additional headers

        Returns:
        -------
            API response as dictionary

        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"

        # Set up headers
        request_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        if headers:
            request_headers.update(headers)

        self._log_api_request("GET", url, request_headers, params or {})

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    url,
                    params=params,
                    headers=request_headers,
                    raise_for_status=True,
                ) as response:
                    result = await response.json()
                    self._log_api_response(
                        response.status,
                        dict(response.headers),
                        result,
                    )
                    return result

            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    self.logger.warning(
                        f"API request failed, attempt {attempt + 1}/{self.max_retries}. "
                        f"Waiting {wait_time}s... Error: {e!s}",
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.exception(
                        f"API request failed after {self.max_retries} attempts: {e!s}",
                    )
                    raise
        return None

    async def web_search(
        self,
        query: str,
        *,
        count: int | None = None,
        offset: int | None = None,
        country: str | None = None,
        search_lang: str | None = None,
        ui_lang: str | None = None,
        safesearch: str | None = None,
        freshness: str | None = None,
        text_decorations: bool | None = None,
        result_filter: str | None = None,
    ) -> dict[str, Any]:
        """Execute a web search query.

        Args:
        ----
            query: Search query string
            count: Number of results (1-20)
            offset: Result offset for pagination
            country: Country code for localization
            search_lang: Search language code
            ui_lang: UI language code
            safesearch: Safe search setting (strict/moderate/off)
            freshness: Time range filter
            text_decorations: Enable text decorations
            result_filter: Filter type for results

        Returns:
        -------
            Dictionary containing search results

        """
        params = {"q": query}

        # Add optional parameters
        if count is not None:
            params["count"] = count
        if offset is not None:
            params["offset"] = offset
        if country:
            params["country"] = country
        if search_lang:
            params["search_lang"] = search_lang
        if ui_lang:
            params["ui_lang"] = ui_lang
        if safesearch:
            params["safesearch"] = safesearch
        if freshness:
            params["freshness"] = freshness
        if text_decorations is not None:
            params["text_decorations"] = text_decorations
        if result_filter:
            params["result_filter"] = result_filter

        return await self._make_request("web/search", params=params)

    async def local_search(
        self,
        query: str,
        *,
        location_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a local business search query.

        Args:
        ----
            query: Search query string (e.g., "restaurants in San Francisco")
            location_ids: Optional list of location IDs to get details for

        Returns:
        -------
            Dictionary containing local search results

        """
        # First get location results
        results = await self.web_search(query)

        # If location IDs are provided, get additional details
        if location_ids:
            poi_results = await self._make_request(
                "local/pois",
                params={"ids": location_ids},
            )

            # Get AI descriptions for locations
            descriptions = await self._make_request(
                "local/descriptions",
                params={"ids": location_ids},
            )

            return {
                "search_results": results,
                "location_details": poi_results,
                "descriptions": descriptions,
            }

        return results

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
