```python
"""APITube News Engine
================

Provides functionality to access news articles from over 350,000 verified sources using the APITube API.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import aiohttp

from .base import BaseEngine


class APITubeEngine(BaseEngine):
    """Research engine for accessing news data using APITube API.

    Provides functionality to:
    - Search news articles by keywords
    - Filter by categories, industries, languages
    - Monitor specific organizations, persons, locations
    - Track sentiment and trends
    - Handle rate limiting and retries
    """

    BASE_URL = "https://api.apitube.io/v1/news"

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3) -> None:
        """Initialize the APITube engine.

        Args:
            api_key: APITube API key. If None, will try to get from environment
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables.

        Raises:
            ValueError: If APITUBE_API_KEY environment variable is not set.

        Returns:
            The API key.
        """
        api_key = os.getenv("APITUBE_API_KEY")
        if not api_key:
            raise ValueError(
                "APITube API key not found. Please set APITUBE_API_KEY environment variable "
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
        """Process method required by BaseEngine.

        Not typically used for this engine as it's primarily accessed via search methods.

        Returns:
            A dictionary indicating the engine is ready.
        """
        return {"status": "APITube engine ready"}

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a request to the APITube API.

        Args:
            endpoint: API endpoint to call
            params: Query parameters
            headers: Additional headers

        Returns:
            API response as dictionary
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"

        # Set up headers
        request_headers = {"Accept": "application/json", "X-API-KEY": self.api_key}
        if headers:
            request_headers.update(headers)

        # Add API key to params
        request_params = params or {}

        self._log_api_request("GET", url, request_headers, request_params)

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    url,
                    params=request_params,
                    headers=request_headers,
                    raise_for_status=True,
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
        *,
        language: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
        industry: Optional[str] = None,
        topic: Optional[str] = None,
        sentiment: Optional[str] = None,
        source_domain: Optional[str] = None,
        organization: Optional[str] = None,
        person: Optional[str] = None,
        location: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Search for news articles with various filters.

        Args:
            query: Search query string
            language: Language code (e.g., 'en', 'es')
            country: Country code (e.g., 'US', 'GB')
            category: News category
            industry: Industry sector
            topic: Specific topic
            sentiment: Sentiment analysis filter
            source_domain: Specific news source domain
            organization: Organization name
            person: Person name
            location: Location name
            from_date: Start date (ISO format)
            to_date: End date (ISO format)
            sort_by: Sort order ('relevance', 'date', etc.)
            page: Page number for pagination
            page_size: Number of results per page

        Returns:
            Dictionary containing news articles and metadata
        """
        params: Dict[str, Any] = {
            "q": query,
            "page": page,
            "page_size": page_size,
        }

        # Add optional parameters
        if language:
            params["language"] = language
        if country:
            params["country"] = country
        if category:
            params["category"] = category
        if industry:
            params["industry"] = industry
        if topic:
            params["topic"] = topic
        if sentiment:
            params["sentiment"] = sentiment
        if source_domain:
            params["source_domain"] = source_domain
        if organization:
            params["organization"] = organization
        if person:
            params["person"] = person
        if location:
            params["location"] = location
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if sort_by:
            params["sort_by"] = sort_by

        return await self._make_request("search", params=params)

    async def trending_topics(
        self,
        *,
        language: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
        industry: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get trending news topics.

        Args:
            language: Language code
            country: Country code
            category: News category
            industry: Industry sector
            timeframe: Time period for trends

        Returns:
            Dictionary containing trending topics
        """
        params: Dict[str, Any] = {}

        # Add optional parameters
        if language:
            params["language"] = language
        if country:
            params["country"] = country
        if category:
            params["category"] = category
        if industry:
            params["industry"] = industry
        if timeframe:
            params["timeframe"] = timeframe

        return await self._make_request("trending", params=params)

    async def sentiment_analysis(
        self,
        query: str,
        *,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get sentiment analysis for news articles.

        Args:
            query: Search query string
            from_date: Start date (ISO format)
            to_date: End date (ISO format)
            language: Language code
            country: Country code

        Returns:
            Dictionary containing sentiment analysis results
        """
        params: Dict[str, Any] = {"q": query}

        # Add optional parameters
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if language:
            params["language"] = language
        if country:
            params["country"] = country

        return await self._make_request("sentiment", params=params)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
```
