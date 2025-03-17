"""
FRED API Engine
==========

Provides functionality to access Federal Reserve Economic Data (FRED) using the FRED API.
"""

import logging
import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List, Union
from .base import BaseEngine


class FREDEngine(BaseEngine):
    """
    Research engine for accessing Federal Reserve Economic Data (FRED).

    Provides functionality to:
    - Access economic data series and observations
    - Get category information and relationships
    - Retrieve release data and schedules
    - Access source information
    - Handle rate limiting and retries
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3) -> None:
        """
        Initialize the FRED engine.

        Args:
            api_key: FRED API key. If None, will try to get from environment
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__()
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.session = None

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        import os
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            raise ValueError(
                "FRED API key not found. Please set FRED_API_KEY environment variable "
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
        return {"status": "FRED engine ready"}

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the FRED API.

        Args:
            endpoint: API endpoint to call
            params: Query parameters

        Returns:
            API response as dictionary
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add API key and format to params
        request_params = params or {}
        request_params["api_key"] = self.api_key
        request_params["file_type"] = "json"

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

    # Category Methods
    async def get_category(self, category_id: int) -> Dict[str, Any]:
        """
        Get a category.

        Args:
            category_id: The ID for a category

        Returns:
            Category details
        """
        return await self._make_request(f"category", params={"category_id": category_id})

    async def get_category_children(
        self,
        category_id: int,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get child categories for a specified parent category.

        Args:
            category_id: The ID for a category
            realtime_start: Start date (YYYY-MM-DD)
            realtime_end: End date (YYYY-MM-DD)

        Returns:
            List of child categories
        """
        params = {"category_id": category_id}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        return await self._make_request("category/children", params=params)

    async def get_category_series(
        self,
        category_id: int,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str = "series_id",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Get the series in a category.

        Args:
            category_id: The ID for a category
            realtime_start: Start date (YYYY-MM-DD)
            realtime_end: End date (YYYY-MM-DD)
            limit: Maximum number of results
            offset: Result offset
            order_by: Order results by values
            sort_order: Sort results in ascending or descending order

        Returns:
            List of series in the category
        """
        params = {
            "category_id": category_id,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "sort_order": sort_order
        }
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        return await self._make_request("category/series", params=params)

    # Series Methods
    async def get_series(
        self,
        series_id: str,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get an economic data series.

        Args:
            series_id: The ID for a series
            realtime_start: Start date (YYYY-MM-DD)
            realtime_end: End date (YYYY-MM-DD)

        Returns:
            Series information
        """
        params = {"series_id": series_id}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        return await self._make_request("series", params=params)

    async def get_series_observations(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None,
        units: str = "lin",
        frequency: Optional[str] = None,
        aggregation_method: str = "avg",
        output_type: int = 1,
        vintage_dates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get the observations or data values for an economic data series.

        Args:
            series_id: The ID for a series
            observation_start: Start date of observations (YYYY-MM-DD)
            observation_end: End date of observations (YYYY-MM-DD)
            realtime_start: Start date for real-time period (YYYY-MM-DD)
            realtime_end: End date for real-time period (YYYY-MM-DD)
            units: Units transformation ('lin', 'chg', 'ch1', 'pch', 'pc1', 'pca', 'cch', 'cca', 'log')
            frequency: Frequency of observations ('d', 'w', 'bw', 'm', 'q', 'sa', 'a')
            aggregation_method: Aggregation method ('avg', 'sum', 'eop')
            output_type: Output type (1=Observations by Real-Time Period, 2=Observations by Vintage Date)
            vintage_dates: List of vintage dates (YYYY-MM-DD)

        Returns:
            Series observations
        """
        params = {
            "series_id": series_id,
            "units": units,
            "aggregation_method": aggregation_method,
            "output_type": output_type
        }
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if frequency:
            params["frequency"] = frequency
        if vintage_dates:
            params["vintage_dates"] = ",".join(vintage_dates)
        return await self._make_request("series/observations", params=params)

    async def search_series(
        self,
        search_text: str,
        search_type: str = "full_text",
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str = "search_rank",
        sort_order: str = "desc",
        filter_variable: Optional[str] = None,
        filter_value: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        exclude_tag_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get economic data series that match search text.

        Args:
            search_text: The words to match against economic data series
            search_type: Type of search ('full_text', 'series_id')
            realtime_start: Start date for real-time period (YYYY-MM-DD)
            realtime_end: End date for real-time period (YYYY-MM-DD)
            limit: Maximum number of results
            offset: Result offset
            order_by: Order results by values
            sort_order: Sort results in ascending or descending order
            filter_variable: The variable to filter against
            filter_value: The value of the filter_variable to filter against
            tag_names: List of tag names that series match all of
            exclude_tag_names: List of tag names that series match none of

        Returns:
            List of matching series
        """
        params = {
            "search_text": search_text,
            "search_type": search_type,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "sort_order": sort_order
        }
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if filter_variable:
            params["filter_variable"] = filter_variable
        if filter_value:
            params["filter_value"] = filter_value
        if tag_names:
            params["tag_names"] = ";".join(tag_names)
        if exclude_tag_names:
            params["exclude_tag_names"] = ";".join(exclude_tag_names)
        return await self._make_request("series/search", params=params)

    # Release Methods
    async def get_releases(
        self,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str = "release_id",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Get all releases of economic data.

        Args:
            realtime_start: Start date for real-time period (YYYY-MM-DD)
            realtime_end: End date for real-time period (YYYY-MM-DD)
            limit: Maximum number of results
            offset: Result offset
            order_by: Order results by values
            sort_order: Sort results in ascending or descending order

        Returns:
            List of releases
        """
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "sort_order": sort_order
        }
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        return await self._make_request("releases", params=params)

    async def get_release_dates(
        self,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str = "release_date",
        sort_order: str = "desc",
        include_release_dates_with_no_data: bool = False
    ) -> Dict[str, Any]:
        """
        Get release dates for all releases of economic data.

        Args:
            realtime_start: Start date for real-time period (YYYY-MM-DD)
            realtime_end: End date for real-time period (YYYY-MM-DD)
            limit: Maximum number of results
            offset: Result offset
            order_by: Order results by values
            sort_order: Sort results in ascending or descending order
            include_release_dates_with_no_data: Include release dates that don't have data

        Returns:
            List of release dates
        """
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "sort_order": sort_order,
            "include_release_dates_with_no_data": include_release_dates_with_no_data
        }
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        return await self._make_request("releases/dates", params=params)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session() 