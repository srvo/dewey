"""
Tavily Research Engine
===================

Provides functionality to perform advanced search queries using the Tavily API.
"""

import logging
import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from .base import BaseEngine


class TavilyEngine(BaseEngine):
    """
    Research engine for performing advanced searches using Tavily API.

    Provides functionality to:
    - Execute general and news-specific searches
    - Handle rate limiting and retries
    - Process and validate responses
    - Support various search configurations
    """

    BASE_URL = "https://api.tavily.com/v1"

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3) -> None:
        """
        Initialize the Tavily engine.

        Args:
            api_key: Tavily API key. If None, will try to get from environment
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.session = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        import os
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError(
                "Tavily API key not found. Please set TAVILY_API_KEY environment variable "
                "or pass api_key to constructor."
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

    async def process(self) -> Dict[str, Any]:
        """
        Process method required by BaseEngine.
        Not typically used for this engine as it's primarily accessed via search methods.
        """
        return {"status": "Tavily engine ready"}

    async def search(
        self,
        query: str,
        *,
        search_depth: str = "basic",
        topic: str = "general",
        max_results: int = 5,
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        include_image_descriptions: bool = False,
        days: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a search query using Tavily API.

        Args:
            query: The search query string
            search_depth: The depth of search ("basic" or "advanced")
            topic: Category of search ("general" or "news")
            max_results: Maximum number of results to return
            include_answer: Include AI-generated answer
            include_raw_content: Include raw HTML content
            include_images: Include related images
            include_image_descriptions: Include image descriptions
            days: Number of days back for news search
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude

        Returns:
            Dictionary containing search results and metadata
        """
        await self._ensure_session()

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions,
        }

        # Add optional parameters only if specified
        if days is not None and topic == "news":
            payload["days"] = days
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        self._log_api_request("POST", f"{self.BASE_URL}/search", {}, payload)

        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.BASE_URL}/search",
                    json=payload,
                    raise_for_status=True
                ) as response:
                    result = await response.json()
                    self._log_api_response(response.status, dict(response.headers), result)
                    return result

            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    self.logger.warning(
                        f"API request failed, attempt {attempt + 1}/{self.max_retries}. "
                        f"Waiting {wait_time}s... Error: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"API request failed after {self.max_retries} attempts: {str(e)}")
                    raise

    async def search_news(
        self,
        query: str,
        days: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a news-specific search query.

        Args:
            query: The search query string
            days: Number of days back to search
            **kwargs: Additional search parameters

        Returns:
            Dictionary containing news search results
        """
        return await self.search(
            query,
            topic="news",
            days=days,
            **kwargs
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session() 