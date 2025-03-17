
# Refactored from: openfigi
# Date: 2025-03-16T16:19:11.263484
# Refactor Version: 1.0
```python
"""OpenFIGI Engine Module

Provides integration with OpenFIGI API for looking up financial instrument identifiers.
Follows the engine pattern used in other research modules.
"""

import os
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import BaseEngine

logger = logging.getLogger(__name__)


class OpenFIGIEngine(BaseEngine):
    """OpenFIGI API integration engine."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the OpenFIGI engine.

        Args:
            api_key: OpenFIGI API key. If not provided, tries to get from environment.
        """
        super().__init__()
        self.api_key: str = api_key or os.getenv('OPENFIGI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenFIGI API key not provided and not found in environment")

        self.last_request_time: float = 0
        self.rate_limit_delay: float = 0.1  # 100ms between requests
        self.batch_size: int = 100  # OpenFIGI batch size limit
        self.max_retries: int = 3
        self.retry_delay: int = 5  # 5 seconds between retries

    def respect_rate_limit(self) -> None:
        """Ensure we don't exceed the OpenFIGI API rate limit."""
        current_time: float = time.time()
        time_since_last_request: float = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_request)
        self.last_request_time = time.time()

    def filter_primary_listing(self, figi_data_list: List[Dict]) -> Optional[Dict]:
        """Filter FIGI data to get the primary listing.

        Prioritizes:
        1. US exchange codes
        2. Common Stock security type
        3. Primary exchange for the region

        Args:
            figi_data_list: List of FIGI data entries

        Returns:
            Primary listing data or None
        """
        # First try to find US common stock
        for data in figi_data_list:
            if (data.get('exchCode') == 'US' and
                    data.get('securityType') == 'Common Stock' and
                    data.get('marketSector') == 'Equity'):
                return data

        # Then try any US listing
        for data in figi_data_list:
            if data.get('exchCode') == 'US':
                return data

        # Then try any common stock
        for data in figi_data_list:
            if data.get('securityType') == 'Common Stock':
                return data

        # Finally, just take the first one
        return figi_data_list[0] if figi_data_list else None

    async def get_figi_data(self, companies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Get FIGI data for a batch of companies.

        Args:
            companies: List of company dictionaries with 'ticker' and other fields

        Returns:
            List of processed FIGI data results
        """
        if not companies:
            return []

        retries: int = 0
        while retries < self.max_retries:
            try:
                self.respect_rate_limit()

                headers: Dict[str, str] = {
                    'X-OPENFIGI-APIKEY': self.api_key,
                    'Content-Type': 'application/json'
                }

                mapping_jobs: List[Dict[str, str]] = [{
                    "idType": "TICKER",
                    "idValue": company["ticker"]
                } for company in companies]

                response: requests.Response = requests.post(
                    'https://api.openfigi.com/v3/mapping',
                    headers=headers,
                    json=mapping_jobs
                )
                response.raise_for_status()
                results: List[Dict[str, Any]] = response.json()

                processed_results: List[Dict[str, Any]] = []
                for idx, result in enumerate(results):
                    company: Dict[str, str] = companies[idx]
                    if "data" in result:
                        # Filter for primary listing
                        primary_listing: Optional[Dict] = self.filter_primary_listing(
                            result["data"])

                        processed_results.append({
                            'ticker': company['ticker'],
                            'security_name': company.get('security_name'),
                            'tick': company.get('tick'),
                            'entity_id': company.get('entity_id'),
                            'figi': primary_listing.get('figi') if primary_listing else None,
                            'market_sector': primary_listing.get('marketSector') if primary_listing else None,
                            'security_type': primary_listing.get('securityType') if primary_listing else None,
                            'exchange_code': primary_listing.get('exchCode') if primary_listing else None,
                            'composite_figi': primary_listing.get('compositeFIGI') if primary_listing else None,
                            'security_description': primary_listing.get('securityDescription') if primary_listing else None,
                            'lookup_status': 'success',
                            'alternative_listings': str(result["data"]) if result.get("data") else '[]'
                        })
                    else:
                        processed_results.append({
                            'ticker': company['ticker'],
                            'security_name': company.get('security_name'),
                            'tick': company.get('tick'),
                            'entity_id': company.get('entity_id'),
                            'figi': None,
                            'market_sector': None,
                            'security_type': None,
                            'exchange_code': None,
                            'composite_figi': None,
                            'security_description': None,
                            'lookup_status': f"failed: {result.get('warning', 'unknown error')}",
                            'alternative_listings': '[]'
                        })

                return processed_results

            except Exception as e:
                logger.error(
                    f"Error processing batch (attempt {retries + 1}): {str(e)}")
                retries += 1
                if retries < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue

                # Return error results after all retries
                return [{
                    'ticker': company['ticker'],
                    'security_name': company.get('security_name'),
                    'tick': company.get('tick'),
                    'entity_id': company.get('entity_id'),
                    'figi': None,
                    'market_sector': None,
                    'security_type': None,
                    'exchange_code': None,
                    'composite_figi': None,
                    'security_description': None,
                    'lookup_status': f"error after {retries} attempts: {str(e)}",
                    'alternative_listings': '[]'
                } for company in companies]

    async def process_batch(self, companies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Process a batch of companies.

        Args:
            companies: List of company dictionaries

        Returns:
            List of processed results
        """
        try:
            return await self.get_figi_data(companies)
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            return []

    async def process_companies(self, companies: List[Dict[str, str]],
                                batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process a list of companies in batches.

        Args:
            companies: List of company dictionaries
            batch_size: Optional batch size. Defaults to self.batch_size

        Returns:
            List of all processed results
        """
        batch_size: int = batch_size or self.batch_size
        results: List[Dict[str, Any]] = []

        for i in range(0, len(companies), batch_size):
            batch: List[Dict[str, str]] = companies[i:i + batch_size]
            logger.info(
                f"Processing batch {i//batch_size + 1} of {(len(companies)-1)//batch_size + 1}")

            batch_results: List[Dict[str, Any]] = await self.process_batch(batch)
            results.extend(batch_results)

        return results
```
