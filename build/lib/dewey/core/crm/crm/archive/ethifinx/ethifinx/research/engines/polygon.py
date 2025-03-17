"""
Polygon API Engine
==============

Provides functionality to access market data, financial information, and news using the Polygon API.
"""

import logging
import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List, Union
from .base import BaseEngine


class PolygonEngine(BaseEngine):
    """
    Research engine for accessing market data using Polygon API.

    Provides functionality to:
    - Access real-time and historical market data
    - Get stock, options, forex, and crypto data
    - Retrieve company information and financials
    - Access news and market analysis
    - Handle rate limiting and retries
    """

    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3) -> None:
        """
        Initialize the Polygon engine.

        Args:
            api_key: Polygon API key. If None, will try to get from environment
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.session = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        import os
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key:
            raise ValueError(
                "Polygon API key not found. Please set POLYGON_API_KEY environment variable "
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
        Not typically used for this engine as it's primarily accessed via data methods.
        """
        return {"status": "Polygon engine ready"}

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Polygon API.

        Args:
            endpoint: API endpoint to call
            params: Query parameters

        Returns:
            API response as dictionary
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add API key to params
        request_params = params or {}
        request_params["apiKey"] = self.api_key

        self._log_api_request("GET", url, {}, request_params)

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    url,
                    params=request_params,
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

    async def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed information about a stock ticker.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Ticker details
        """
        return await self._make_request(f"v3/reference/tickers/{symbol}")

    async def get_ticker_news(
        self,
        symbol: str,
        limit: int = 100,
        order: str = "desc",
        sort: str = "published_utc"
    ) -> Dict[str, Any]:
        """
        Get news articles for a ticker.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of results
            order: Sort order ('asc' or 'desc')
            sort: Field to sort by

        Returns:
            List of news articles
        """
        params = {
            "ticker": symbol,
            "limit": limit,
            "order": order,
            "sort": sort
        }
        return await self._make_request("v2/reference/news", params=params)

    async def get_aggregates(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        from_date: str,
        to_date: str,
        adjusted: bool = True,
        sort: str = "asc",
        limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Get aggregated price data.

        Args:
            symbol: Stock ticker symbol
            multiplier: Size of the timespan multiplier
            timespan: Size of the time window ('minute', 'hour', 'day', 'week', 'month', 'quarter', 'year')
            from_date: From date (YYYY-MM-DD)
            to_date: To date (YYYY-MM-DD)
            adjusted: Whether to include split/dividend adjustments
            sort: Sort direction ('asc' or 'desc')
            limit: Maximum number of results

        Returns:
            Aggregated price data
        """
        params = {
            "adjusted": str(adjusted).lower(),
            "sort": sort,
            "limit": limit
        }
        return await self._make_request(
            f"v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}",
            params=params
        )

    async def get_daily_open_close(
        self,
        symbol: str,
        date: str,
        adjusted: bool = True
    ) -> Dict[str, Any]:
        """
        Get daily open/close price data.

        Args:
            symbol: Stock ticker symbol
            date: Date in format YYYY-MM-DD
            adjusted: Whether to include split/dividend adjustments

        Returns:
            Daily open/close data
        """
        params = {"adjusted": str(adjusted).lower()}
        return await self._make_request(
            f"v1/open-close/{symbol}/{date}",
            params=params
        )

    async def get_previous_close(
        self,
        symbol: str,
        adjusted: bool = True
    ) -> Dict[str, Any]:
        """
        Get previous day's open/close price data.

        Args:
            symbol: Stock ticker symbol
            adjusted: Whether to include split/dividend adjustments

        Returns:
            Previous day's price data
        """
        params = {"adjusted": str(adjusted).lower()}
        return await self._make_request(
            f"v2/aggs/ticker/{symbol}/prev",
            params=params
        )

    async def get_trades(
        self,
        symbol: str,
        date: str,
        timestamp: Optional[int] = None,
        order: str = "asc",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get trades for a ticker symbol.

        Args:
            symbol: Stock ticker symbol
            date: Date in format YYYY-MM-DD
            timestamp: Timestamp to start from
            order: Sort order ('asc' or 'desc')
            limit: Maximum number of results

        Returns:
            List of trades
        """
        params = {
            "order": order,
            "limit": limit
        }
        if timestamp:
            params["timestamp"] = timestamp

        return await self._make_request(
            f"v3/trades/{symbol}/{date}",
            params=params
        )

    async def get_quotes(
        self,
        symbol: str,
        date: str,
        timestamp: Optional[int] = None,
        order: str = "asc",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get quotes for a ticker symbol.

        Args:
            symbol: Stock ticker symbol
            date: Date in format YYYY-MM-DD
            timestamp: Timestamp to start from
            order: Sort order ('asc' or 'desc')
            limit: Maximum number of results

        Returns:
            List of quotes
        """
        params = {
            "order": order,
            "limit": limit
        }
        if timestamp:
            params["timestamp"] = timestamp

        return await self._make_request(
            f"v3/quotes/{symbol}/{date}",
            params=params
        )

    async def get_financials(
        self,
        symbol: str,
        limit: int = 5,
        type: str = "Y",
        sort: str = "reportPeriod"
    ) -> Dict[str, Any]:
        """
        Get financial statements for a company.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of results
            type: Report type ('Y'=Annual, 'Q'=Quarterly, 'T'=Trailing)
            sort: Field to sort by

        Returns:
            Financial statements data
        """
        params = {
            "ticker": symbol,
            "limit": limit,
            "type": type,
            "sort": sort
        }
        return await self._make_request("v2/reference/financials", params=params)

    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status.

        Returns:
            Market status information
        """
        return await self._make_request("v1/marketstatus/now")

    async def get_market_holidays(self) -> Dict[str, Any]:
        """
        Get market holidays.

        Returns:
            List of market holidays
        """
        return await self._make_request("v1/marketstatus/upcoming")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session() 