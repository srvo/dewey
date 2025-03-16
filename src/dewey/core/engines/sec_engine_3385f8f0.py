```python
"""SEC EDGAR API Engine.

Provides functionality to access SEC EDGAR data using the SEC API.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp

from .base import BaseEngine


class SECEngine(BaseEngine):
    """Research engine for accessing SEC EDGAR data.

    Provides functionality to:
    - Access company filings and submissions
    - Get company information and metadata
    - Retrieve financial statements and disclosures
    - Access mutual fund data
    - Handle rate limiting and retries
    """

    BASE_URL = "https://data.sec.gov"
    COMPANY_URL = "https://www.sec.gov/files/company_tickers.json"
    USER_AGENT = "EthiFinX Research Engine/1.0"

    def __init__(self, max_retries: int = 3) -> None:
        """Initialize the SEC engine.

        Args:
            max_retries: Maximum number of retry attempts for failed requests.
        """
        super().__init__()
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self.session is None:
            headers = {"User-Agent": self.USER_AGENT, "Accept": "application/json"}
            self.session = aiohttp.ClientSession(headers=headers)

    async def _close_session(self) -> None:
        """Close aiohttp session if it exists."""
        if self.session:
            await self.session.close()
            self.session = None

    async def process(self) -> Dict[str, Any]:
        """Process method required by BaseEngine.

        Not typically used for this engine as it's primarily accessed via data methods.
        """
        return {"status": "SEC engine ready"}

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make a request to the SEC API.

        Args:
            endpoint: API endpoint to call.
            params: Query parameters.
            base_url: Override default base URL.

        Returns:
            API response as dictionary.
        """
        await self._ensure_session()

        url = f"{base_url or self.BASE_URL}/{endpoint}"
        request_params = params or {}

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
                    wait_time = (attempt + 1) * 10  # Longer backoff for SEC API
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

    async def get_company_tickers(self) -> Dict[str, Any]:
        """Get list of all company tickers.

        Returns:
            Dictionary of company tickers and CIK numbers.
        """
        return await self._make_request("", base_url=self.COMPANY_URL)

    async def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Get company concept data for a specific company.

        Args:
            cik: Company CIK number (10 digits, zero-padded).

        Returns:
            Company facts data.
        """
        cik = str(cik).zfill(10)
        return await self._make_request(f"api/xbrl/companyfacts/CIK{cik}.json")

    async def get_company_concept(
        self, cik: str, taxonomy: str, concept: str
    ) -> Dict[str, Any]:
        """Get a specific company concept.

        Args:
            cik: Company CIK number (10 digits, zero-padded).
            taxonomy: Taxonomy name (e.g., 'us-gaap').
            concept: Concept name (e.g., 'Assets').

        Returns:
            Company concept data.
        """
        cik = str(cik).zfill(10)
        return await self._make_request(
            f"api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json"
        )

    async def get_submissions(self, cik: str) -> Dict[str, Any]:
        """Get company submissions history.

        Args:
            cik: Company CIK number (10 digits, zero-padded).

        Returns:
            Company submissions data.
        """
        cik = str(cik).zfill(10)
        return await self._make_request(f"api/submissions/CIK{cik}.json")

    async def get_company_filings(
        self,
        cik: str,
        form_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get company filings.

        Args:
            cik: Company CIK number (10 digits, zero-padded).
            form_type: Type of form (e.g., '10-K', '10-Q', '8-K').
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).

        Returns:
            Company filings data.
        """
        cik = str(cik).zfill(10)
        params: Dict[str, Any] = {}
        if form_type:
            params["form"] = form_type
        if start_date:
            params["dateRange"] = "custom"
            params["startDate"] = start_date
            params["endDate"] = end_date or start_date
        return await self._make_request(
            f"api/submissions/CIK{cik}/filings.json", params=params
        )

    async def get_mutual_fund_search(
        self,
        ticker: Optional[str] = None,
        series_id: Optional[str] = None,
        cik: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for mutual fund data.

        Args:
            ticker: Fund ticker symbol.
            series_id: Fund series ID.
            cik: Company CIK number.

        Returns:
            Mutual fund search results.
        """
        params: Dict[str, Any] = {}
        if ticker:
            params["ticker"] = ticker
        if series_id:
            params["seriesId"] = series_id
        if cik:
            params["cik"] = str(cik).zfill(10)
        return await self._make_request("api/investment/search", params=params)

    async def get_mutual_fund_series(self, series_id: str) -> Dict[str, Any]:
        """Get mutual fund series data.

        Args:
            series_id: Fund series ID.

        Returns:
            Mutual fund series data.
        """
        return await self._make_request(f"api/investment/series/{series_id}")

    async def get_mutual_fund_classes(self, series_id: str) -> Dict[str, Any]:
        """Get mutual fund class data.

        Args:
            series_id: Fund series ID.

        Returns:
            Mutual fund class data.
        """
        return await self._make_request(
            f"api/investment/series/{series_id}/classes"
        )

    async def get_company_financial_statements(
        self, cik: str, form_type: str = "10-K", filing_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get company financial statements from a specific filing.

        Args:
            cik: Company CIK number (10 digits, zero-padded).
            form_type: Type of form (e.g., '10-K', '10-Q').
            filing_date: Filing date (YYYY-MM-DD).

        Returns:
            Financial statements data.
        """
        cik = str(cik).zfill(10)
        params: Dict[str, Any] = {"form": form_type}
        if filing_date:
            params["filingDate"] = filing_date
        return await self._make_request(
            f"api/xbrl/companyfiling/CIK{cik}/financials.json", params=params
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
```
