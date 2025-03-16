import contextlib
import logging
import time
from datetime import datetime

import duckdb
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_stock_history(ticker, start_date=None, end_date=None, max_retries=3):
    """Fetch historical data for a single stock.
    If start_date is None, fetches all available history from IPO date.
    """
    for attempt in range(max_retries):
        try:
            ticker_obj = yf.Ticker(ticker)

            # Get max history if start_date not specified
            if start_date is None:
                # period='max' gets all available data from IPO
                df = ticker_obj.history(period="max")
            else:
                df = ticker_obj.history(start=start_date, end=end_date)

            if df.empty:
                logger.warning(f"No data found for {ticker}")
                return None

            # Reset index to make Date a column and rename columns
            df = df.reset_index()
            df.columns = [x.lower().replace(" ", "_") for x in df.columns]

            # Convert date to string in ISO format for DuckDB
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df["ticker"] = ticker

            # Add data source and timestamp columns
            df["data_source"] = "yahoo"
            df["last_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logger.info(
                f"Fetched {len(df)} records for {ticker} from {df['date'].min()} to {df['date'].max()}",
            )
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Exponential backoff
                logger.warning(
                    f"Error fetching {ticker}, attempt {attempt + 1}/{max_retries}. Waiting {wait_time}s... Error: {e!s}",
                )
                time.sleep(wait_time)
            else:
                logger.exception(
                    f"Failed to fetch {ticker} after {max_retries} attempts: {e!s}",
                )
                return None
    return None


def create_tables(conn) -> None:
    """Create necessary tables if they don't exist."""
    try:
        # Drop existing views and tables
        conn.execute("DROP VIEW IF EXISTS price_history_coverage")
        conn.execute("DROP VIEW IF EXISTS latest_stock_prices")
        conn.execute("DROP TABLE IF EXISTS stock_daily_prices")

        conn.execute(
            """
            CREATE TABLE stock_daily_prices (
                ticker VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                dividends DOUBLE DEFAULT 0,
                stock_splits DOUBLE DEFAULT 1,
                data_source VARCHAR,
                last_updated_at TIMESTAMP,
                is_in_current_universe BOOLEAN,
                PRIMARY KEY (ticker, date)
            )
        """,
        )

        # Create view for latest prices
        conn.execute(
            """
            CREATE VIEW latest_stock_prices AS
            WITH ranked_prices AS (
                SELECT
                    ticker,
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    dividends,
                    stock_splits,
                    data_source,
                    last_updated_at,
                    is_in_current_universe,
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
                FROM stock_daily_prices
            )
            SELECT
                ticker,
                date,
                open,
                high,
                low,
                close,
                volume,
                dividends,
                stock_splits,
                data_source,
                last_updated_at,
                is_in_current_universe
            FROM ranked_prices
            WHERE rn = 1
        """,
        )

        # Create view for data coverage analysis
        conn.execute(
            """
            CREATE VIEW price_history_coverage AS
            SELECT
                p.ticker,
                MIN(p.date) as first_date,
                MAX(p.date) as last_date,
                COUNT(*) as total_days,
                CAST(COUNT(*) AS DOUBLE) / (DATEDIFF('day', MIN(p.date), MAX(p.date)) + 1) as completeness_pct,
                cu.tick
            FROM stock_daily_prices p
            LEFT JOIN current_universe cu ON p.ticker = cu.ticker
            GROUP BY p.ticker, cu.tick
            ORDER BY cu.tick DESC NULLS LAST
        """,
        )
    except Exception as e:
        logger.exception(f"Error creating tables: {e!s}")
        with contextlib.suppress(Exception):
            conn.execute("ROLLBACK")
        raise


def batch_upsert(conn, df, batch_size=50, max_retries=3):
    """Handle batch upsert with DuckDB's limitations."""
    total_rows = len(df)
    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        batch_df = df.iloc[start_idx:end_idx].copy()

        # Convert dates to strings in ISO format
        if not isinstance(batch_df["date"].iloc[0], str):
            batch_df["date"] = batch_df["date"].dt.strftime("%Y-%m-%d")
        if not isinstance(batch_df["last_updated_at"].iloc[0], str):
            batch_df["last_updated_at"] = batch_df["last_updated_at"].apply(
                lambda x: x.strftime("%Y-%m-%d %H:%M:%S"),
            )

        for attempt in range(max_retries):
            current_conn = conn  # Use the passed connection first

            try:
                # First try to insert
                try:
                    current_conn.execute("BEGIN TRANSACTION")

                    # Insert with explicit type casting
                    insert_sql = """
                        INSERT INTO stock_daily_prices (
                            ticker, date, open, high, low, close, volume,
                            dividends, stock_splits, data_source, last_updated_at,
                            is_in_current_universe
                        )
                        SELECT
                            CAST(? AS VARCHAR) as ticker,
                            CAST(? AS DATE) as date,
                            CAST(? AS DOUBLE) as open,
                            CAST(? AS DOUBLE) as high,
                            CAST(? AS DOUBLE) as low,
                            CAST(? AS DOUBLE) as close,
                            CAST(? AS BIGINT) as volume,
                            CAST(? AS DOUBLE) as dividends,
                            CAST(? AS DOUBLE) as stock_splits,
                            CAST(? AS VARCHAR) as data_source,
                            CAST(? AS TIMESTAMP) as last_updated_at,
                            CAST(? AS BOOLEAN) as is_in_current_universe
                    """

                    # Insert row by row to better handle type conversion
                    for _, row in batch_df.iterrows():
                        current_conn.execute(
                            insert_sql,
                            [
                                row["ticker"],
                                row["date"],
                                row["open"],
                                row["high"],
                                row["low"],
                                row["close"],
                                row["volume"],
                                row.get("dividends", 0),
                                row.get("stock_splits", 1),
                                row["data_source"],
                                row["last_updated_at"],
                                row["is_in_current_universe"],
                            ],
                        )

                    current_conn.execute("COMMIT")
                    break

                except duckdb.ConstraintException:
                    # If insert fails, do update
                    current_conn.execute("ROLLBACK")
                    current_conn.execute("BEGIN TRANSACTION")

                    update_sql = """
                        UPDATE stock_daily_prices
                        SET
                            open = CAST(? AS DOUBLE),
                            high = CAST(? AS DOUBLE),
                            low = CAST(? AS DOUBLE),
                            close = CAST(? AS DOUBLE),
                            volume = CAST(? AS BIGINT),
                            dividends = CAST(? AS DOUBLE),
                            stock_splits = CAST(? AS DOUBLE),
                            data_source = CAST(? AS VARCHAR),
                            last_updated_at = CAST(? AS TIMESTAMP),
                            is_in_current_universe = CAST(? AS BOOLEAN)
                        WHERE ticker = ? AND date = CAST(? AS DATE)
                    """

                    for _, row in batch_df.iterrows():
                        current_conn.execute(
                            update_sql,
                            [
                                row["open"],
                                row["high"],
                                row["low"],
                                row["close"],
                                row["volume"],
                                row.get("dividends", 0),
                                row.get("stock_splits", 1),
                                row["data_source"],
                                row["last_updated_at"],
                                row["is_in_current_universe"],
                                row["ticker"],
                                row["date"],
                            ],
                        )

                    current_conn.execute("COMMIT")
                    break

            except Exception as e:
                with contextlib.suppress(Exception):
                    current_conn.execute("ROLLBACK")

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 15
                    logger.warning(
                        f"Database error, attempt {attempt + 1}/{max_retries}. Waiting {wait_time}s... Error: {e!s}",
                    )
                    time.sleep(wait_time)

                    # Try to reconnect
                    with contextlib.suppress(Exception):
                        current_conn.close()
                    try:
                        current_conn = duckdb.connect("md:port5")
                        conn = current_conn  # Update the main connection if reconnect succeeds
                    except Exception as conn_error:
                        logger.exception(f"Failed to reconnect: {conn_error!s}")
                else:
                    logger.exception(
                        f"Failed database operation after {max_retries} attempts: {e!s}",
                    )
                    raise

        # Small pause between batches
        time.sleep(0.5)  # Reduced pause time

    return conn  # Return the potentially updated connection


def main() -> None:
    """Main function to fetch and store stock price data."""
    conn = None
    try:
        # Connect to DuckDB
        conn = duckdb.connect("md:port5")

        # Create tables
        create_tables(conn)

        # Get universe of stocks to process
        universe_query = """
            SELECT
                cu.ticker,
                cu.tick as tick_rating,
                COALESCE(
                    MAX(p.date) >= CURRENT_DATE - INTERVAL 7 DAY,
                    FALSE
                ) as has_current_data
            FROM current_universe cu
            LEFT JOIN stock_daily_prices p ON cu.ticker = p.ticker
            GROUP BY cu.ticker, cu.tick
            ORDER BY cu.tick DESC NULLS LAST, has_current_data ASC
        """

        try:
            universe_df = conn.execute(universe_query).df()
        except Exception as e:
            logger.exception(f"Error fetching universe: {e!s}")
            raise

        if len(universe_df) == 0:
            logger.warning("No stocks found in universe")
            return

        # Log universe status
        logger.info(
            f"""
            Universe Status:
            - Total tickers: {len(universe_df)}
            - New tickers: {len(universe_df[~universe_df['has_current_data']])}
            - Stale tickers: 0
            - Current tickers: {len(universe_df[universe_df['has_current_data']])}
            - Tick rating range: {universe_df['tick_rating'].min():.2f} to {universe_df['tick_rating'].max():.2f}
            - Average tick rating: {universe_df['tick_rating'].mean():.2f}
            """,
        )

        # Process each stock
        for _, row in tqdm(
            universe_df.iterrows(),
            total=len(universe_df),
            desc="Fetching stock data",
        ):
            ticker = row["ticker"]
            tick_rating = row["tick_rating"]

            logger.info(f"Processing {ticker} (tick rating: {tick_rating})")

            try:
                # Fetch data from Yahoo Finance
                df = fetch_stock_history(ticker)
                if df is None or len(df) == 0:
                    continue

                # Add metadata
                df["data_source"] = "yahoo"
                df["last_updated_at"] = pd.Timestamp.now()
                df["is_in_current_universe"] = True

                # Save to database and get potentially updated connection
                conn = batch_upsert(conn, df)

            except Exception as e:
                logger.exception(f"Error processing {ticker}: {e!s}")
                # Try to reconnect if we lost connection
                with contextlib.suppress(Exception):
                    conn.close()
                try:
                    conn = duckdb.connect("md:port5")
                except Exception as conn_error:
                    logger.exception(f"Failed to reconnect: {conn_error!s}")
                    raise
                continue

        # Log completion
        coverage_query = """
            SELECT
                COUNT(DISTINCT ticker) as total_tickers,
                COUNT(*) as total_records,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                AVG(completeness_pct) as avg_completeness
            FROM price_history_coverage
        """

        try:
            coverage_df = conn.execute(coverage_query).df()
            logger.info(
                f"""
                Data Coverage Summary:
                - Total tickers: {coverage_df['total_tickers'].iloc[0]}
                - Total records: {coverage_df['total_records'].iloc[0]:,}
                - Date range: {coverage_df['earliest_date'].iloc[0]} to {coverage_df['latest_date'].iloc[0]}
                - Average completeness: {coverage_df['avg_completeness'].iloc[0]:.1%}
            """,
            )
        except Exception as e:
            logger.exception(f"Error getting coverage stats: {e!s}")

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Saving current progress...")
        if conn:
            try:
                coverage_df = conn.execute(coverage_query).df()
                logger.info(
                    f"Saved {coverage_df['total_records'].iloc[0]:,} records before interrupt",
                )
            except Exception as e:
                logger.exception(f"Error saving progress after interrupt: {e!s}")
    finally:
        if conn:
            with contextlib.suppress(Exception):
                conn.close()


if __name__ == "__main__":
    main()
