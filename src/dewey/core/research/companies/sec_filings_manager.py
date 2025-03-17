
# Refactored from: sec_filings_manager
# Date: 2025-03-16T16:19:11.391541
# Refactor Version: 1.0
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sec_edgar import company, filings


class SECFilingsManager:
    def __init__(self, cache_dir="sec_cache") -> None:
        """Initialize SEC filings manager with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    async def get_company_filings(
        self,
        ticker: str,
        filing_types=None,
        start_date=None,
        end_date=None,
    ):
        """Fetch SEC filings for a company asynchronously.

        Args:
        ----
            ticker (str): Company ticker symbol
            filing_types (list): List of filing types (e.g., ['10-K', '10-Q'])
            start_date (datetime): Start date for filings search
            end_date (datetime): End date for filings search

        Returns:
        -------
            pd.DataFrame: DataFrame containing filing information

        """
        if filing_types is None:
            filing_types = ["10-K", "10-Q", "8-K"]

        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        try:
            # Create company object
            company.Company(ticker)

            # Get filings
            filing_list = []
            for filing_type in filing_types:
                filings_data = filings.get_filings(
                    cik_or_ticker=ticker,
                    filing_type=filing_type,
                    start_date=start_date,
                    end_date=end_date,
                )

                for filing in filings_data:
                    filing_info = {
                        "ticker": ticker,
                        "type": filing_type,
                        "date": filing.date,
                        "accession_number": filing.accession_number,
                        "file_number": filing.file_number,
                        "url": filing.url,
                    }
                    filing_list.append(filing_info)

            # Convert to DataFrame
            df = pd.DataFrame(filing_list)

            # Cache the results
            cache_file = self.cache_dir / f"{ticker}_filings.csv"
            df.to_csv(cache_file, index=False)

            return df

        except Exception:
            return pd.DataFrame()

    def get_cached_filings(self, ticker: str) -> pd.DataFrame:
        """Get cached filings for a company."""
        cache_file = self.cache_dir / f"{ticker}_filings.csv"
        if cache_file.exists():
            return pd.read_csv(cache_file)
        return pd.DataFrame()

    def clear_cache(self, ticker: str | None = None) -> None:
        """Clear cache for a specific ticker or all tickers."""
        if ticker:
            cache_file = self.cache_dir / f"{ticker}_filings.csv"
            if cache_file.exists():
                os.remove(cache_file)
        else:
            for file in self.cache_dir.glob("*_filings.csv"):
                os.remove(file)
