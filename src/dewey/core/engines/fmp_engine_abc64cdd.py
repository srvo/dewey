```python
"""Financial Modeling Prep Engine
==========================

Provides functionality to access financial data, statements, and market
information using the FMP API.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

import aiohttp

from .base import BaseEngine


class FMPEngine(BaseEngine):
    """Research engine for accessing financial data using Financial Modeling Prep API.

    Provides functionality to:
        - Access company financial statements
        - Get real-time and historical stock prices
        - Retrieve company profiles and metrics
        - Access market performance data
        - Handle rate limiting and retries
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3) -> None:
        """Initialize the FMP engine.

        Args:
            api_key: FMP API key. If None, will try to get from environment.
            max_retries: Maximum number of retry attempts for failed requests.
        """
        super().__init__()
        self.api_key: str = api_key or self._get_api_key()
        self.max_retries: int = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables.

        Raises:
            ValueError: If the FMP_API_KEY environment variable is not set.

        Returns:
            The API key.
        """
        api_key = os.getenv("FMP_API_KEY")
        if not api_key:
            raise ValueError(
                "FMP API key not found. Please set FMP_API_KEY environment variable "
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

        Not typically used for this engine as it's primarily accessed via data
        methods.
        """
        return {"status": "FMP engine ready"}

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the FMP API.

        Args:
            endpoint: API endpoint to call.
            params: Query parameters.

        Returns:
            API response as dictionary.
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"

        # Add API key to params
        request_params = params or {}
        request_params["apikey"] = self.api_key

        self._log_api_request("GET", url, {}, request_params)

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    url, params=request_params, raise_for_status=True
                ) as response:
                    result = await response.json()
                    self._log_api_response(
                        response.status, dict(response.headers), result
                    )
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
                    self.logger.error(
                        f"API request failed after {self.max_retries} attempts: {str(e)}"
                    )
                    raise

    async def search_company(
        self,
        query: str,
        limit: Optional[int] = None,
        exchange: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for companies by name or symbol.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            exchange: Filter by specific exchange.

        Returns:
            List of matching companies.
        """
        params = {"query": query}
        if limit:
            params["limit"] = limit
        if exchange:
            params["exchange"] = exchange

        return await self._make_request("search", params=params)

    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get detailed company profile information.

        Args:
            symbol: Company stock symbol.

        Returns:
            Company profile data.
        """
        return await self._make_request(f"profile/{symbol}")

    async def get_quote(self, symbol: Union[str, List[str]]) -> List[Dict[str, Any]]:
        """Get real-time stock quote data.

        Args:
            symbol: Single stock symbol or list of symbols.

        Returns:
            List of stock quotes.
        """
        if isinstance(symbol, list):
            symbol = ",".join(symbol)
        return await self._make_request(f"quote/{symbol}")

    async def get_financial_statements(
        self,
        symbol: str,
        statement: str = "income",
        period: str = "annual",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get company financial statements.

        Args:
            symbol: Company stock symbol.
            statement: Statement type ('income', 'balance', 'cash').
            period: Period type ('annual', 'quarter').
            limit: Number of periods to return.

        Returns:
            List of financial statements.
        """
        endpoint = {
            "income": "income-statement",
            "balance": "balance-sheet-statement",
            "cash": "cash-flow-statement",
        }.get(statement, "income-statement")

        params = {"period": period, "limit": limit}

        return await self._make_request(f"{endpoint}/{symbol}", params=params)

    async def get_key_metrics(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get company key metrics.

        Args:
            symbol: Company stock symbol.
            period: Period type ('annual', 'quarter').
            limit: Number of periods to return.

        Returns:
            List of key metrics.
        """
        params = {"period": period, "limit": limit}

        return await self._make_request(f"key-metrics/{symbol}", params=params)

    async def get_financial_ratios(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get company financial ratios.

        Args:
            symbol: Company stock symbol.
            period: Period type ('annual', 'quarter').
            limit: Number of periods to return.

        Returns:
            List of financial ratios.
        """
        params = {"period": period, "limit": limit}

        return await self._make_request(f"ratios/{symbol}", params=params)

    async def get_historical_price(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        timeseries: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get historical stock prices.

        Args:
            symbol: Company stock symbol.
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
            timeseries: Number of data points to return.

        Returns:
            List of historical prices.
        """
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if timeseries:
            params["timeseries"] = timeseries

        return await self._make_request(
            f"historical-price-full/{symbol}", params=params
        )

    async def get_market_indexes(self) -> List[Dict[str, Any]]:
        """Get list of available market indexes.

        Returns:
            List of market indexes.
        """
        return await self._make_request("symbol/available-indexes")

    async def get_stock_list(self) -> List[Dict[str, Any]]:
        """Get list of all available stocks.

        Returns:
            List of stocks.
        """
        return await self._make_request("stock/list")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
```
