"""
Yahoo Finance Research Engine
==========================

Provides functionality to fetch market data from Yahoo Finance.
"""

import logging
import pandas as pd
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .base import BaseEngine


class YahooFinanceEngine(BaseEngine):
    """
    Research engine for fetching market data from Yahoo Finance.

    Provides functionality to:
    - Fetch historical price data
    - Handle rate limiting and retries
    - Process and validate data
    - Store results in standardized format
    """

    def __init__(self, max_retries: int = 3) -> None:
        """
        Initialize the Yahoo Finance engine.

        Args:
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__()
        self.max_retries = max_retries

    async def process(self) -> Dict[str, Any]:
        """
        Process method required by BaseEngine.
        Not typically used for this engine as it's primarily accessed via fetch_history.
        """
        return {"status": "YahooFinance engine ready"}

    def fetch_history(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a single stock.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for historical data (None for max history)
            end_date: End date for historical data (None for current date)

        Returns:
            DataFrame with historical price data or None if fetch fails
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Fetching data for {ticker} (attempt {attempt + 1}/{self.max_retries})")
                
                ticker_obj = yf.Ticker(ticker)
                
                # Get max history if start_date not specified
                if start_date is None:
                    df = ticker_obj.history(period='max')
                else:
                    df = ticker_obj.history(start=start_date, end=end_date)
                    
                if df.empty:
                    self.logger.warning(f"No data found for {ticker}")
                    return None
                
                # Process the dataframe
                df = self._process_dataframe(df, ticker)
                
                self.logger.info(
                    f"Fetched {len(df)} records for {ticker} "
                    f"from {df['date'].min()} to {df['date'].max()}"
                )
                return df

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    self.logger.warning(
                        f"Error fetching {ticker}, attempt {attempt + 1}/{self.max_retries}. "
                        f"Waiting {wait_time}s... Error: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to fetch {ticker} after {self.max_retries} attempts: {str(e)}")
                    return None

    def _process_dataframe(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Process raw Yahoo Finance dataframe into standardized format.

        Args:
            df: Raw dataframe from Yahoo Finance
            ticker: Stock ticker symbol

        Returns:
            Processed dataframe with standardized columns and metadata
        """
        # Reset index to make Date a column
        df = df.reset_index()
        
        # Standardize column names
        df.columns = [x.lower().replace(' ', '_') for x in df.columns]
        
        # Convert date to string in ISO format
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # Add metadata columns
        df['ticker'] = ticker
        df['data_source'] = 'yahoo'
        df['last_updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return df

    def fetch_batch(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch historical data for multiple stocks.

        Args:
            tickers: List of stock ticker symbols
            start_date: Start date for historical data (None for max history)
            end_date: End date for historical data (None for current date)

        Returns:
            Dictionary mapping tickers to their respective DataFrames
        """
        results = {}
        for ticker in tickers:
            try:
                df = self.fetch_history(ticker, start_date, end_date)
                results[ticker] = df
            except Exception as e:
                self.logger.error(f"Error processing {ticker}: {str(e)}")
                results[ticker] = None
        
        return results 