import datetime
import os
from typing import Any

import duckdb
import pandas as pd
import requests
from dewey.core.base_script import BaseScript
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TICK_API_URL = "https://api.polygon.io/v2/ticks/stocks/{ticker}/{date}"
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
DUCKDB_PATH = "/Users/srvo/dewey/data/ticks.duckdb"
TABLE_NAME = "stock_ticks"
SCHEMA = {
    "ticker": "VARCHAR",
    "trade_id": "BIGINT",
    "timestamp": "TIMESTAMP",
    "price": "DOUBLE",
    "size": "INT",
    "conditions": "VARCHAR",
    "sequence_number": "BIGINT",
}


class TickProcessor(BaseScript):
    """Processes stock tick data from Polygon.io and stores it in a DuckDB database."""

    def __init__(self) -> None:
        """Initializes the TickProcessor with configuration, database connection, and logging."""
        super().__init__(
            name="TickProcessor",
            description="Processes stock tick data from Polygon.io and stores it in a DuckDB database.",
            config_section="tick_processor",
            requires_db=True,
            enable_llm=False,
        )

    def _fetch_ticks(self, ticker: str, date: datetime.date) -> list[dict[str, Any]]:
        """
        Fetches stock tick data from the Polygon.io API for a given ticker and date.

        Args:
        ----
            ticker: The stock ticker symbol (e.g., "AAPL").
            date: The date for which to fetch tick data.

        Returns:
        -------
            A list of dictionaries, where each dictionary represents a stock tick.

        Raises:
        ------
            requests.exceptions.RequestException: If there is an error during the API request.

        """
        url = TICK_API_URL.format(ticker=ticker, date=date.strftime("%Y-%m-%d"))
        params = {"apiKey": POLYGON_API_KEY, "limit": 50000}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            if data["status"] == "OK" and "results" in data:
                return data["results"]
            self.logger.warning(
                f"No results found for {ticker} on {date}: {data.get('error')}",
            )
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for {ticker} on {date}: {e}")
            raise

    def _transform_ticks(
        self, ticks: list[dict[str, Any]], ticker: str,
    ) -> pd.DataFrame:
        """
        Transforms raw tick data into a Pandas DataFrame with appropriate data types.

        Args:
        ----
            ticks: A list of dictionaries representing raw tick data.
            ticker: The stock ticker symbol.

        Returns:
        -------
            A Pandas DataFrame containing the transformed tick data.

        """
        df = pd.DataFrame(ticks)
        if df.empty:
            return df

        # Rename columns to match the schema
        df = df.rename(
            columns={
                "T": "timestamp",
                "p": "price",
                "s": "size",
                "c": "conditions",
                "t": "trade_id",
                "q": "sequence_number",
            },
        )

        # Apply transformations
        df["ticker"] = ticker
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df["conditions"] = df["conditions"].apply(
            lambda x: ",".join(x),
        )  # Join conditions list

        # Select and reorder columns
        df = df[
            [
                "ticker",
                "trade_id",
                "timestamp",
                "price",
                "size",
                "conditions",
                "sequence_number",
            ]
        ]

        return df

    def _store_ticks(self, df: pd.DataFrame) -> None:
        """
        Stores the transformed tick data into the DuckDB database.

        Args:
        ----
            df: A Pandas DataFrame containing the transformed tick data.

        """
        if df.empty:
            self.logger.info("No data to store.")
            return

        try:
            con = duckdb.connect(DUCKDB_PATH)
            con.execute("SET timezone='UTC'")  # Enforce UTC timezone
            con.register("tick_data", df)  # Register DataFrame

            # Construct and execute the SQL query
            query = f"""
                INSERT INTO {TABLE_NAME}
                SELECT ticker, trade_id, timestamp, price, size, conditions, sequence_number
                FROM tick_data
            """
            con.execute(query)
            self.logger.info(f"Successfully stored {len(df)} ticks in {TABLE_NAME}")

        except Exception as e:
            self.logger.error(f"Error storing ticks in the database: {e}")
            raise
        finally:
            if con:
                con.close()

    def run(self) -> None:
        """Runs the tick processing workflow for a specific ticker and date."""
        ticker = "AAPL"  # Example ticker
        date = datetime.date(2024, 1, 2)  # Example date

        self.logger.info(f"Processing ticks for {ticker} on {date}")

        try:
            # 1. Fetch ticks
            ticks = self._fetch_ticks(ticker, date)

            # 2. Transform ticks
            df = self._transform_ticks(ticks, ticker)

            # 3. Store ticks
            if not df.empty:
                self._store_ticks(df)
            else:
                self.logger.info("No data to store after transformation.")

            self.logger.info(f"Tick processing completed for {ticker} on {date}")

        except Exception as e:
            self.logger.error(f"Tick processing failed for {ticker} on {date}: {e}")


if __name__ == "__main__":
    processor = TickProcessor()
    processor.execute()
