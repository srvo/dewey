"""
Exa AI Research Engine
===================

Provides functionality to perform AI-optimized searches using the Exa API.
"""

import logging
import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List, Union
from .base import BaseEngine


class ExaEngine(BaseEngine):
    """
    Research engine for performing AI-optimized searches using Exa API.

    Provides functionality to:
    - Execute embeddings-based searches
    - Retrieve clean, parsed HTML content
    - Find semantically similar pages
    - Handle rate limiting and retries
    """

    BASE_URL = "https://api.exa.ai"

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3) -> None:
        """
        Initialize the Exa engine.

        Args:
            api_key: Exa API key. If None, will try to get from environment
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.session = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        import os
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise ValueError(
                "Exa API key not found. Please set EXA_API_KEY environment variable "
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
        return {"status": "Exa engine ready"}

    async def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Exa API.

        Args:
            endpoint: API endpoint to call
            payload: Request payload
            headers: Additional headers

        Returns:
            API response as dictionary
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"
        
        # Set up headers
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        if headers:
            request_headers.update(headers)

        self._log_api_request("POST", url, request_headers, payload)

        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    headers=request_headers,
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

    async def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        use_autoprompt: bool = True,
        highlights: bool = True,
        text: bool = True,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an embeddings-based or keyword search.

        Args:
            query: Search query string
            num_results: Number of results to return
            use_autoprompt: Use Exa's query enhancement
            highlights: Include highlighted text snippets
            text: Include full text content
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            start_published_date: Start date filter (ISO format)
            end_published_date: End date filter (ISO format)

        Returns:
            Dictionary containing search results
        """
        payload = {
            "query": query,
            "num_results": num_results,
            "use_autoprompt": use_autoprompt,
            "highlights": highlights,
            "text": text,
        }

        # Add optional parameters
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        if start_published_date:
            payload["start_published_date"] = start_published_date
        if end_published_date:
            payload["end_published_date"] = end_published_date

        return await self._make_request("search", payload)

    async def get_contents(
        self,
        urls: List[str],
        *,
        text: bool = True,
        highlights: bool = False,
        html: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve clean, parsed content from URLs.

        Args:
            urls: List of URLs to fetch content from
            text: Include parsed text content
            highlights: Include highlighted text snippets
            html: Include cleaned HTML

        Returns:
            Dictionary containing parsed contents
        """
        payload = {
            "urls": urls,
            "text": text,
            "highlights": highlights,
            "html": html,
        }

        return await self._make_request("contents", payload)

    async def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
        highlights: bool = True,
        text: bool = True,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Find pages semantically similar to a given URL.

        Args:
            url: URL to find similar pages for
            num_results: Number of results to return
            highlights: Include highlighted text snippets
            text: Include full text content
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude

        Returns:
            Dictionary containing similar pages
        """
        payload = {
            "url": url,
            "num_results": num_results,
            "highlights": highlights,
            "text": text,
        }

        # Add optional parameters
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        return await self._make_request("findsimilar", payload)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session() 