#!/usr/bin/env python3
import logging
import os
from datetime import datetime, timedelta

import duckdb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connections():
    """Get connections to both local DuckDB and MotherDuck."""
    local_conn = duckdb.connect("data/local.duckdb")

    # Connect to MotherDuck if token is available
    md_conn = None
    md_token = os.getenv("MOTHERDUCK_TOKEN")
    if md_token:
        try:
            md_conn = duckdb.connect(f"md:port5?token={md_token}")
            logger.info("Connected to MotherDuck successfully")
        except Exception as e:
            logger.exception(f"Failed to connect to MotherDuck: {e}")

    return local_conn, md_conn


def sync_current_universe(local_conn, md_conn) -> None:
    """Sync current universe from MotherDuck to local DuckDB."""
    if not md_conn:
        logger.warning("No MotherDuck connection available, skipping sync")
        return

    # Get current universe from MotherDuck
    stocks = md_conn.execute(
        """
        SELECT
            ticker,
            security_name as name,
            COALESCE(sector, category, 'Unknown') as sector,
            COALESCE(category, sector, 'Unknown') as industry
        FROM current_universe
        WHERE ticker IS NOT NULL
            AND security_name IS NOT NULL
            AND workflow IS NOT NULL  -- Only include stocks with a workflow
            AND workflow != 'excluded'  -- Exclude explicitly excluded stocks
            AND workflow != 'ignore'  -- Exclude ignored stocks
    """,
    ).fetchdf()

    # Create and populate table in local DuckDB
    local_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS current_universe (
            ticker VARCHAR PRIMARY KEY,
            name VARCHAR,
            sector VARCHAR,
            industry VARCHAR
        )
    """,
    )

    # Clear existing data
    local_conn.execute("DELETE FROM current_universe")

    # Insert new data
    local_conn.execute("INSERT INTO current_universe SELECT * FROM stocks")
    local_conn.commit()

    logger.info(f"Synced {len(stocks)} stocks to current_universe table")


def get_current_universe(conn) -> list[dict]:
    """Get the current universe of stocks."""
    stocks_df = conn.execute(
        """
        -- Get stocks from current universe and join with tracked_stocks to get their IDs
        SELECT DISTINCT
            cu.ticker,
            cu.name,
            cu.sector,
            cu.industry
        FROM current_universe cu
        JOIN tracked_stocks ts ON
            -- Match either direct symbol or CIK-based symbol
            ts.symbol = cu.ticker
            OR ts.entity_id = REPLACE(ts.symbol, 'C', '')
        ORDER BY cu.sector, cu.industry, cu.ticker
    """,
    ).fetchdf()

    stocks = []
    for _, row in stocks_df.iterrows():
        stocks.append(
            {
                "ticker": row["ticker"],
                "name": row["name"],
                "sector": row["sector"],
                "industry": row["industry"],
            },
        )

    return stocks


def analyze_financial_changes(conn, ticker: str) -> dict:
    """Analyze significant financial metric changes."""
    # Get the last 2 months of financial metrics
    two_months_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    metrics = conn.execute(
        """
        WITH MetricChanges AS (
            SELECT
                metric_name,
                value as current_value,
                LAG(value) OVER (PARTITION BY metric_name ORDER BY end_date) as prev_value,
                end_date,
                filed_date
            FROM financial_metrics fm
            JOIN tracked_stocks ts ON fm.stock_id = ts.id
            JOIN current_universe cu ON
                -- Match either direct symbol or CIK-based symbol
                (ts.symbol = cu.ticker OR ts.entity_id = REPLACE(ts.symbol, 'C', ''))
            WHERE cu.ticker = ?
                AND end_date >= ?
                AND metric_namespace = 'us-gaap'
                AND metric_name IN (
                    'Assets', 'Liabilities', 'Revenues', 'NetIncomeLoss',
                    'OperatingIncomeLoss', 'StockholdersEquity',
                    'CashAndCashEquivalentsAtCarryingValue'
                )
            ORDER BY end_date DESC
        )
        SELECT
            metric_name,
            current_value,
            prev_value,
            end_date,
            filed_date,
            CASE
                WHEN prev_value = 0 OR prev_value IS NULL THEN NULL
                ELSE ((current_value - prev_value) / ABS(prev_value)) * 100
            END as pct_change
        FROM MetricChanges
        WHERE current_value IS NOT NULL
            AND prev_value IS NOT NULL
            AND ABS(CASE
                WHEN prev_value = 0 OR prev_value IS NULL THEN 0
                ELSE ((current_value - prev_value) / ABS(prev_value)) * 100
            END) > 20  -- Only show significant changes (>20%)
    """,
        [ticker, two_months_ago],
    ).fetchdf()

    return metrics.to_dict("records") if not metrics.empty else []


def analyze_material_events(conn, ticker: str) -> list[str]:
    """Analyze material events from SEC filings."""
    # Get recent filings
    two_months_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    events = []

    # Look for significant events in financial metrics
    changes = analyze_financial_changes(conn, ticker)
    for change in changes:
        metric = change["metric_name"]
        pct_change = change["pct_change"]
        date = change["end_date"].strftime("%Y-%m-%d")

        if abs(pct_change) > 50:  # Very significant change
            events.append(
                f"MAJOR CHANGE: {metric} {'increased' if pct_change > 0 else 'decreased'} by {pct_change:.1f}% as of {date}",
            )
        else:
            events.append(
                f"Significant change in {metric}: {'increased' if pct_change > 0 else 'decreased'} by {pct_change:.1f}% as of {date}",
            )

    # Look for specific material events in filings
    material_events = conn.execute(
        """
        SELECT DISTINCT
            form,
            filed_date,
            metric_name,
            value,
            start_date,
            end_date
        FROM financial_metrics fm
        JOIN tracked_stocks ts ON fm.stock_id = ts.id
        JOIN current_universe cu ON
            -- Match either direct symbol or CIK-based symbol
            (ts.symbol = cu.ticker OR ts.entity_id = REPLACE(ts.symbol, 'C', ''))
        WHERE cu.ticker = ?
            AND filed_date >= ?
            AND form IN ('8-K', '10-Q', '10-K')
            AND (
                metric_name LIKE '%Restructuring%'
                OR metric_name LIKE '%Acquisition%'
                OR metric_name LIKE '%Impairment%'
                OR metric_name LIKE '%Discontinued%'
                OR metric_name LIKE '%LitigationSettlement%'
                OR metric_name LIKE '%BusinessCombination%'
                OR metric_name LIKE '%Merger%'
                OR metric_name LIKE '%Disposal%'
                OR metric_name LIKE '%Settlement%'
                OR metric_name LIKE '%Termination%'
                OR metric_name LIKE '%Severance%'
            )
        ORDER BY filed_date DESC
    """,
        [ticker, two_months_ago],
    ).fetchdf()

    if not material_events.empty:
        for _, event in material_events.iterrows():
            events.append(
                f"Material event ({event['form']} filed {event['filed_date'].strftime('%Y-%m-%d')}): {event['metric_name']}",
            )

    return events


def main() -> None:
    try:
        # Get database connections
        local_conn, md_conn = get_db_connections()
        logger.info("Connected to databases")

        # Sync current universe from MotherDuck
        sync_current_universe(local_conn, md_conn)

        # Get current universe
        stocks = get_current_universe(local_conn)
        logger.info(f"Found {len(stocks)} stocks in current universe")

        # Analyze each stock
        material_findings = []

        for stock in stocks:
            ticker = stock["ticker"]
            logger.info(
                f"\nAnalyzing {ticker} ({stock['name']}) - {stock['sector']}/{stock['industry']}...",
            )

            events = analyze_material_events(local_conn, ticker)
            if events:
                material_findings.append(
                    {
                        "ticker": ticker,
                        "name": stock["name"],
                        "sector": stock["sector"],
                        "industry": stock["industry"],
                        "events": events,
                    },
                )

        # Print summary of material findings
        if material_findings:
            # Group by sector
            by_sector = {}
            for finding in material_findings:
                sector = finding["sector"]
                if sector not in by_sector:
                    by_sector[sector] = []
                by_sector[sector].append(finding)

            # Print findings by sector
            for sector, findings in by_sector.items():
                for finding in findings:
                    for _event in finding["events"]:
                        pass
        else:
            pass

        # Close connections
        local_conn.close()
        if md_conn:
            md_conn.close()

        logger.info("\nAnalysis completed successfully")

    except Exception as e:
        logger.exception(f"Error during analysis: {e!s}")
        import traceback

        logger.exception(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
