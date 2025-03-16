#!/usr/bin/env python3
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
EXTRACTED_DIR = Path("data/sec/extracted")
LOCAL_DB_PATH = "data/local.duckdb"
MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")
MOTHERDUCK_DB = "port5"  # Database for Port 5.0 stocks


def get_db_connections():
    """Get connections to both local DuckDB and MotherDuck."""
    # Connect to local DuckDB
    local_conn = duckdb.connect(LOCAL_DB_PATH)

    # Connect to MotherDuck if token is available
    md_conn = None
    if MOTHERDUCK_TOKEN:
        try:
            md_conn = duckdb.connect(f"md:{MOTHERDUCK_DB}?token={MOTHERDUCK_TOKEN}")
            logger.info("Connected to MotherDuck successfully")
        except Exception as e:
            logger.exception(f"Failed to connect to MotherDuck: {e}")

    return local_conn, md_conn


def initialize_schema(conn) -> None:
    """Initialize the database schema."""
    # Create sequences first
    conn.execute("CREATE SEQUENCE IF NOT EXISTS tracked_stocks_id_seq")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS stock_analysis_id_seq")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS financial_metrics_id_seq")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tracked_stocks (
            id BIGINT PRIMARY KEY DEFAULT nextval('tracked_stocks_id_seq'),
            symbol VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            added_date TIMESTAMP NOT NULL,
            notes TEXT,
            entity_id VARCHAR
        )
    """,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_analysis (
            id BIGINT PRIMARY KEY DEFAULT nextval('stock_analysis_id_seq'),
            stock_id INTEGER,
            timestamp TIMESTAMP NOT NULL,
            price DOUBLE,
            market_cap DOUBLE,
            pe_ratio DOUBLE,
            industry VARCHAR,
            fundamental_changes JSON,
            market_insights TEXT
        )
    """,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_metrics (
            id BIGINT PRIMARY KEY DEFAULT nextval('financial_metrics_id_seq'),
            stock_id INTEGER,
            metric_name VARCHAR NOT NULL,
            metric_namespace VARCHAR NOT NULL,
            value DOUBLE,
            unit VARCHAR,
            start_date DATE,
            end_date DATE,
            filed_date DATE,
            form VARCHAR,
            frame VARCHAR,
            UNIQUE(stock_id, metric_name, start_date, end_date, filed_date)
        )
    """,
    )


def extract_all_metrics(data, stock_id):
    """Extract all financial metrics from SEC data."""
    metrics_data = []
    facts = data.get("facts", {})

    for namespace, namespace_data in facts.items():
        for metric_name, metric_data in namespace_data.items():
            for unit, values in metric_data.get("units", {}).items():
                for value in values:
                    metrics_data.append(
                        {
                            "stock_id": stock_id,
                            "metric_name": metric_name,
                            "metric_namespace": namespace,
                            "value": value.get("val"),
                            "unit": unit,
                            "start_date": value.get("start"),
                            "end_date": value.get("end"),
                            "filed_date": value.get("filed"),
                            "form": value.get("form"),
                            "frame": value.get("frame"),
                        },
                    )

    return metrics_data


def store_financial_metrics(conn, stock_id, metrics, filing_date) -> None:
    """Store financial metrics in the database."""
    for metric_name, metric_data in metrics.items():
        conn.execute(
            """
            INSERT INTO financial_metrics
            (id, stock_id, metric_name, metric_namespace, value, unit, start_date, end_date, filed_date, form, frame)
            SELECT
                nextval('financial_metrics_id_seq'),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        """,
            [
                stock_id,
                metric_name,
                metric_data.get("namespace", ""),
                metric_data.get("value"),
                metric_data.get("unit", ""),
                metric_data.get("start_date"),
                metric_data.get("end_date"),
                filing_date,
                metric_data.get("form", ""),
                metric_data.get("frame", ""),
            ],
        )


def store_company_data(conn, company_data):
    """Store company data in the database."""
    # Insert company info and get the ID
    result = conn.execute(
        """
        INSERT INTO tracked_stocks (symbol, name, added_date, entity_id)
        VALUES (?, ?, ?, ?)
        RETURNING id
    """,
        (
            company_data["symbol"],
            company_data["name"],
            datetime.now().replace(microsecond=0),  # Remove timezone and microseconds
            company_data["cik"],
        ),
    ).fetchone()

    return result[0]


def create_financial_views(conn) -> None:
    """Create views for financial analysis."""
    # Create a view for the latest financial metrics
    conn.execute(
        """
        CREATE OR REPLACE VIEW latest_financials AS
        WITH RankedMetrics AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY filed_date DESC, end_date DESC
                ) as rn
            FROM financial_metrics
        )
        SELECT
            ts.symbol,
            ts.name,
            rm.metric_name,
            rm.metric_namespace,
            rm.value,
            rm.unit,
            rm.start_date,
            rm.end_date,
            rm.filed_date,
            rm.form
        FROM RankedMetrics rm
        JOIN tracked_stocks ts ON rm.stock_id = ts.id
        WHERE rn = 1
    """,
    )

    # Create a view for financial metrics time series
    conn.execute(
        """
        CREATE OR REPLACE VIEW financial_time_series AS
        SELECT
            ts.symbol,
            ts.name,
            fm.metric_name,
            fm.metric_namespace,
            fm.value,
            fm.unit,
            fm.start_date,
            fm.end_date,
            fm.filed_date,
            fm.form
        FROM financial_metrics fm
        JOIN tracked_stocks ts ON fm.stock_id = ts.id
        ORDER BY ts.symbol, fm.metric_name, fm.end_date DESC
    """,
    )

    # Create period-over-period comparison view
    conn.execute(
        """
        CREATE OR REPLACE VIEW period_over_period AS
        WITH CurrentPeriod AS (
            SELECT
                stock_id,
                metric_name,
                value as current_value,
                end_date as current_end_date,
                ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date DESC
                ) as rn
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
        ),
        PriorPeriod AS (
            SELECT
                stock_id,
                metric_name,
                value as prior_value,
                end_date as prior_end_date,
                ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date DESC
                ) as rn
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
        )
        SELECT
            ts.symbol,
            ts.name,
            cp.metric_name,
            cp.current_value,
            cp.current_end_date,
            pp.prior_value,
            pp.prior_end_date,
            CASE
                WHEN pp.prior_value = 0 THEN NULL
                ELSE ((cp.current_value - pp.prior_value) / pp.prior_value) * 100
            END as percentage_change,
            (cp.current_value - pp.prior_value) as absolute_change
        FROM CurrentPeriod cp
        JOIN PriorPeriod pp ON cp.stock_id = pp.stock_id
            AND cp.metric_name = pp.metric_name
            AND cp.rn = 1
            AND pp.rn = 2
        JOIN tracked_stocks ts ON cp.stock_id = ts.id
        WHERE cp.current_value IS NOT NULL
            AND pp.prior_value IS NOT NULL
        ORDER BY ts.symbol, cp.metric_name
    """,
    )

    # Create quarterly trend view
    conn.execute(
        """
        CREATE OR REPLACE VIEW quarterly_trends AS
        WITH QuarterlyMetrics AS (
            SELECT
                stock_id,
                metric_name,
                value,
                end_date,
                ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date DESC
                ) as quarter_num
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
                AND form LIKE '10-Q%'
            ORDER BY end_date DESC
            LIMIT 4
        )
        SELECT
            ts.symbol,
            ts.name,
            qm.metric_name,
            qm.value,
            qm.end_date,
            qm.quarter_num
        FROM QuarterlyMetrics qm
        JOIN tracked_stocks ts ON qm.stock_id = ts.id
        ORDER BY ts.symbol, qm.metric_name, qm.quarter_num
    """,
    )

    # Create industry comparison view
    conn.execute(
        """
        CREATE OR REPLACE VIEW industry_comparison AS
        WITH KeyMetrics AS (
            SELECT
                stock_id,
                metric_name,
                value,
                ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date DESC
                ) as rn
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
                AND metric_name IN (
                    'Assets', 'Liabilities', 'Revenues', 'NetIncomeLoss',
                    'OperatingIncomeLoss', 'StockholdersEquity'
                )
        ),
        IndustryStats AS (
            SELECT
                cu.sector,
                km.metric_name,
                COUNT(*) as company_count,
                AVG(km.value) as industry_avg,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY km.value) as industry_median,
                MIN(km.value) as industry_min,
                MAX(km.value) as industry_max
            FROM KeyMetrics km
            JOIN tracked_stocks ts ON km.stock_id = ts.id
            JOIN current_universe cu ON ts.symbol = cu.ticker
            WHERE km.rn = 1
            GROUP BY cu.sector, km.metric_name
        )
        SELECT
            ts.symbol,
            ts.name,
            cu.sector,
            km.metric_name,
            km.value as company_value,
            is.industry_avg,
            is.industry_median,
            is.company_count as peer_count,
            CASE
                WHEN is.industry_avg = 0 THEN NULL
                ELSE (km.value - is.industry_avg) / is.industry_avg * 100
            END as pct_diff_from_avg,
            NTILE(100) OVER (
                PARTITION BY cu.sector, km.metric_name
                ORDER BY km.value
            ) as percentile_rank
        FROM KeyMetrics km
        JOIN tracked_stocks ts ON km.stock_id = ts.id
        JOIN current_universe cu ON ts.symbol = cu.ticker
        JOIN IndustryStats is ON cu.sector = is.sector
            AND km.metric_name = is.metric_name
        WHERE km.rn = 1
        ORDER BY cu.sector, km.metric_name, km.value DESC
    """,
    )

    # Create sector performance view
    conn.execute(
        """
        CREATE OR REPLACE VIEW sector_performance AS
        WITH SectorMetrics AS (
            SELECT
                cu.sector,
                fm.metric_name,
                COUNT(DISTINCT ts.id) as company_count,
                AVG(CASE
                    WHEN fm.metric_name IN ('NetIncomeLoss', 'OperatingIncomeLoss')
                    THEN fm.value / NULLIF(LAG(fm.value) OVER (
                        PARTITION BY ts.id, fm.metric_name
                        ORDER BY fm.end_date
                    ), 0) - 1
                    ELSE NULL
                END) * 100 as avg_growth_rate,
                AVG(fm.value) as avg_value,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fm.value) as median_value
            FROM financial_metrics fm
            JOIN tracked_stocks ts ON fm.stock_id = ts.id
            JOIN current_universe cu ON ts.symbol = cu.ticker
            WHERE fm.metric_namespace = 'us-gaap'
                AND fm.metric_name IN (
                    'Revenues', 'NetIncomeLoss', 'OperatingIncomeLoss',
                    'Assets', 'Liabilities', 'StockholdersEquity'
                )
            GROUP BY cu.sector, fm.metric_name
        )
        SELECT
            sector,
            metric_name,
            company_count,
            avg_growth_rate,
            avg_value,
            median_value,
            RANK() OVER (
                PARTITION BY metric_name
                ORDER BY avg_value DESC
            ) as sector_rank_by_value,
            RANK() OVER (
                PARTITION BY metric_name
                ORDER BY avg_growth_rate DESC NULLS LAST
            ) as sector_rank_by_growth
        FROM SectorMetrics
        ORDER BY sector, metric_name
    """,
    )

    # Create advanced growth metrics view
    conn.execute(
        """
        CREATE OR REPLACE VIEW advanced_growth_metrics AS
        WITH MetricHistory AS (
            SELECT
                stock_id,
                metric_name,
                value,
                end_date,
                LAG(value, 1) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                ) as prev_value,
                LAG(value, 4) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                ) as year_ago_value,
                LAG(value, 12) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                ) as three_year_ago_value
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
                AND metric_name IN (
                    'Revenues', 'NetIncomeLoss', 'OperatingIncomeLoss',
                    'Assets', 'StockholdersEquity'
                )
        )
        SELECT
            ts.symbol,
            ts.name,
            mh.metric_name,
            mh.value as current_value,
            mh.end_date,
            -- Quarter-over-Quarter Growth
            CASE
                WHEN mh.prev_value = 0 OR mh.prev_value IS NULL THEN NULL
                ELSE ((mh.value - mh.prev_value) / ABS(mh.prev_value)) * 100
            END as qoq_growth,
            -- Year-over-Year Growth
            CASE
                WHEN mh.year_ago_value = 0 OR mh.year_ago_value IS NULL THEN NULL
                ELSE ((mh.value - mh.year_ago_value) / ABS(mh.year_ago_value)) * 100
            END as yoy_growth,
            -- 3-Year CAGR
            CASE
                WHEN mh.three_year_ago_value = 0 OR mh.three_year_ago_value IS NULL THEN NULL
                ELSE (POWER(mh.value / mh.three_year_ago_value, 1.0/3.0) - 1) * 100
            END as cagr_3_year,
            -- Growth Stability (Standard Deviation of quarterly growth)
            STDDEV_SAMP(
                CASE
                    WHEN mh.prev_value = 0 OR mh.prev_value IS NULL THEN NULL
                    ELSE ((mh.value - mh.prev_value) / ABS(mh.prev_value)) * 100
                END
            ) OVER (
                PARTITION BY ts.symbol, mh.metric_name
                ORDER BY mh.end_date
                ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
            ) as growth_volatility
        FROM MetricHistory mh
        JOIN tracked_stocks ts ON mh.stock_id = ts.id
        WHERE mh.value IS NOT NULL
        ORDER BY ts.symbol, mh.metric_name, mh.end_date DESC
    """,
    )

    # Create financial ratios view
    conn.execute(
        """
        CREATE OR REPLACE VIEW financial_ratios AS
        WITH LatestMetrics AS (
            SELECT
                stock_id,
                metric_name,
                value,
                ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date DESC
                ) as rn
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
        ),
        PivotedMetrics AS (
            SELECT
                stock_id,
                MAX(CASE WHEN metric_name = 'Assets' THEN value END) as total_assets,
                MAX(CASE WHEN metric_name = 'Liabilities' THEN value END) as total_liabilities,
                MAX(CASE WHEN metric_name = 'StockholdersEquity' THEN value END) as equity,
                MAX(CASE WHEN metric_name = 'Revenues' THEN value END) as revenue,
                MAX(CASE WHEN metric_name = 'NetIncomeLoss' THEN value END) as net_income,
                MAX(CASE WHEN metric_name = 'OperatingIncomeLoss' THEN value END) as operating_income,
                MAX(CASE WHEN metric_name = 'CashAndCashEquivalentsAtCarryingValue' THEN value END) as cash,
                MAX(CASE WHEN metric_name = 'AccountsReceivableNetCurrent' THEN value END) as receivables,
                MAX(CASE WHEN metric_name = 'InventoryNet' THEN value END) as inventory,
                MAX(CASE WHEN metric_name = 'AccountsPayableCurrent' THEN value END) as payables,
                MAX(CASE WHEN metric_name = 'LongTermDebtNoncurrent' THEN value END) as long_term_debt,
                MAX(CASE WHEN metric_name = 'CostOfGoodsAndServicesSold' THEN value END) as cogs,
                MAX(CASE WHEN metric_name = 'OperatingExpenses' THEN value END) as operating_expenses
            FROM LatestMetrics
            WHERE rn = 1
            GROUP BY stock_id
        )
        SELECT
            ts.symbol,
            ts.name,
            -- Profitability Ratios
            (pm.net_income / NULLIF(pm.revenue, 0)) * 100 as net_profit_margin,
            (pm.operating_income / NULLIF(pm.revenue, 0)) * 100 as operating_margin,
            (pm.net_income / NULLIF(pm.equity, 0)) * 100 as roe,
            (pm.net_income / NULLIF(pm.total_assets, 0)) * 100 as roa,

            -- Efficiency Ratios
            (pm.revenue / NULLIF(pm.total_assets, 0)) as asset_turnover,
            CASE
                WHEN pm.receivables IS NOT NULL AND pm.revenue IS NOT NULL AND pm.receivables > 0
                THEN (pm.receivables / (pm.revenue / 365))
                ELSE NULL
            END as days_sales_outstanding,
            CASE
                WHEN pm.inventory IS NOT NULL AND pm.cogs IS NOT NULL AND pm.inventory > 0
                THEN (pm.inventory / (pm.cogs / 365))
                ELSE NULL
            END as days_inventory_outstanding,

            -- Liquidity Ratios
            (pm.cash + pm.receivables) / NULLIF(pm.total_liabilities, 0) as quick_ratio,
            (pm.cash + pm.receivables + pm.inventory) / NULLIF(pm.total_liabilities, 0) as current_ratio,

            -- Leverage Ratios
            pm.total_liabilities / NULLIF(pm.equity, 0) as debt_to_equity,
            pm.long_term_debt / NULLIF(pm.equity, 0) as long_term_debt_to_equity,

            -- Operating Ratios
            (pm.operating_expenses / NULLIF(pm.revenue, 0)) * 100 as operating_expense_ratio,
            ((pm.revenue - pm.cogs) / NULLIF(pm.revenue, 0)) * 100 as gross_margin

        FROM PivotedMetrics pm
        JOIN tracked_stocks ts ON pm.stock_id = ts.id
        ORDER BY ts.symbol
    """,
    )

    # Create risk metrics view
    conn.execute(
        """
        CREATE OR REPLACE VIEW risk_metrics AS
        WITH MetricVolatility AS (
            SELECT
                stock_id,
                metric_name,
                -- Calculate volatility over different periods
                STDDEV_SAMP(value) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                    ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
                ) as volatility_quarterly,
                STDDEV_SAMP(value) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                    ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                ) as volatility_annual,
                -- Calculate trend stability
                REGR_R2(value, ROW_NUMBER() OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                )) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                    ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                ) as trend_stability,
                -- Calculate relative volatility to sector
                value / AVG(value) OVER (
                    PARTITION BY metric_name, end_date
                ) as relative_performance,
                end_date
            FROM financial_metrics
            WHERE metric_namespace = 'us-gaap'
                AND metric_name IN (
                    'Revenues', 'NetIncomeLoss', 'OperatingIncomeLoss',
                    'Assets', 'Liabilities', 'StockholdersEquity'
                )
        ),
        RiskScores AS (
            SELECT
                stock_id,
                metric_name,
                -- Normalize volatilities to create risk scores
                (volatility_quarterly / MAX(volatility_quarterly) OVER (PARTITION BY metric_name)) * 100 as quarterly_risk_score,
                (volatility_annual / MAX(volatility_annual) OVER (PARTITION BY metric_name)) * 100 as annual_risk_score,
                -- Score trend stability (higher is better)
                COALESCE(trend_stability * 100, 0) as trend_stability_score,
                -- Score relative performance volatility
                STDDEV_SAMP(relative_performance) OVER (
                    PARTITION BY stock_id, metric_name
                    ORDER BY end_date
                    ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                ) * 100 as relative_volatility_score,
                end_date
            FROM MetricVolatility
        )
        SELECT
            ts.symbol,
            ts.name,
            rs.metric_name,
            rs.end_date,
            rs.quarterly_risk_score,
            rs.annual_risk_score,
            rs.trend_stability_score,
            rs.relative_volatility_score,
            -- Calculate composite risk score (lower is better)
            (
                rs.quarterly_risk_score * 0.3 +
                rs.annual_risk_score * 0.3 +
                (100 - rs.trend_stability_score) * 0.2 +
                rs.relative_volatility_score * 0.2
            ) as composite_risk_score,
            -- Risk categories
            CASE
                WHEN rs.annual_risk_score < 30 AND rs.trend_stability_score > 70 THEN 'Low Risk'
                WHEN rs.annual_risk_score > 70 OR rs.trend_stability_score < 30 THEN 'High Risk'
                ELSE 'Medium Risk'
            END as risk_category
        FROM RiskScores rs
        JOIN tracked_stocks ts ON rs.stock_id = ts.id
        ORDER BY ts.symbol, rs.metric_name, rs.end_date DESC
    """,
    )


def load_cik_lookup():
    """Load CIK to ticker/name mapping from SEC lookup file."""
    lookup = {}
    try:
        with open("data/sec/cik-lookup-data.txt") as f:
            for line in f:
                # Format is: NAME:CIK:TICKER:EXCHANGE
                parts = line.strip().split(":")
                if len(parts) >= 3:
                    name, cik, ticker = parts[0:3]
                    if ticker:  # Only store if ticker exists
                        lookup[cik.zfill(10)] = {
                            "ticker": ticker,
                            "name": name,
                        }
    except FileNotFoundError:
        logger.warning("CIK lookup file not found, will use generated symbols")
    return lookup


def process_company_files(local_conn, md_conn=None) -> None:
    """Process all company files in the data directory."""
    initialize_schema(local_conn)
    if md_conn:
        initialize_schema(md_conn)

    # Load CIK lookup data
    cik_lookup = load_cik_lookup()

    data_dir = Path("data/sec/extracted")
    company_files = list(data_dir.glob("*.json"))
    logger.info(f"Found {len(company_files)} company files")

    # Batch processing data structures
    companies_batch = []
    metrics_batch = []
    analysis_batch = []
    batch_size = 1000  # Process 1000 companies at a time

    companies_processed = 0
    companies_added = 0

    for file_path in tqdm(company_files):
        try:
            companies_processed += 1

            with open(file_path) as f:
                data = json.load(f)

            # Extract company info
            cik = str(data.get("cik")).zfill(10)  # CIK should be 10 digits
            company_name = data.get("entityName")

            if not (cik and company_name):
                continue

            # Get latest metrics
            metrics = get_latest_financial_metrics(data)
            most_recent_filing = get_most_recent_filing_date(data)

            # Try to get ticker from lookup, fall back to generated symbol
            lookup_data = cik_lookup.get(cik)
            if lookup_data:
                symbol = lookup_data["ticker"]
                company_name = lookup_data["name"]  # Use standardized name
            else:
                symbol = f"C{cik[-8:]}"  # Fallback to generated symbol

            # Add to companies batch
            companies_batch.append(
                {
                    "symbol": symbol,
                    "name": company_name,
                    "added_date": datetime.now().replace(microsecond=0),
                    "entity_id": cik,
                },
            )

            if metrics:
                # Prepare metrics batch
                for metric_name, metric_data in metrics.items():
                    metrics_batch.append(
                        {
                            "symbol": symbol,  # We'll join with companies table later
                            "metric_name": metric_name,
                            "metric_namespace": metric_data.get("namespace", ""),
                            "value": metric_data.get("value"),
                            "unit": metric_data.get("unit", ""),
                            "start_date": metric_data.get("start_date"),
                            "end_date": metric_data.get("end_date"),
                            "filed_date": most_recent_filing,
                            "form": metric_data.get("form", ""),
                            "frame": metric_data.get("frame", ""),
                        },
                    )

                # Prepare analysis batch
                market_cap = metrics.get("Assets", {}).get("value")
                pe_ratio = metrics.get("EarningsPerShareBasic", {}).get("value")
                analysis_batch.append(
                    {
                        "symbol": symbol,  # We'll join with companies table later
                        "timestamp": datetime.now().replace(microsecond=0),
                        "market_cap": market_cap,
                        "pe_ratio": pe_ratio,
                        "fundamental_changes": json.dumps(metrics),
                        "market_insights": f"Data from SEC filings as of {most_recent_filing}",
                    },
                )

            companies_added += 1

            # Process batch when it reaches the batch size
            if len(companies_batch) >= batch_size:
                _process_batch(
                    local_conn,
                    md_conn,
                    companies_batch,
                    metrics_batch,
                    analysis_batch,
                )
                companies_batch = []
                metrics_batch = []
                analysis_batch = []
                logger.info(
                    f"Processed {companies_processed} companies, added {companies_added}",
                )

        except Exception as e:
            logger.exception(f"Error processing {file_path}: {e!s}")
            continue

    # Process remaining batch
    if companies_batch:
        _process_batch(
            local_conn,
            md_conn,
            companies_batch,
            metrics_batch,
            analysis_batch,
        )

    # Create views after all data is loaded
    logger.info("Creating analysis views...")
    create_financial_views(local_conn)
    if md_conn:
        create_financial_views(md_conn)

    logger.info(
        f"Completed! Processed {companies_processed} companies, added {companies_added}",
    )


def _process_batch(conn, md_conn, companies, metrics, analysis) -> None:
    """Process a batch of companies and their associated data."""
    try:
        # Convert to DataFrames for bulk insert
        pd.DataFrame(companies)
        metrics_df = pd.DataFrame(metrics) if metrics else None
        analysis_df = pd.DataFrame(analysis) if analysis else None

        logger.info(
            f"Processing batch: {len(companies)} companies, {len(metrics) if metrics else 0} metrics, {len(analysis) if analysis else 0} analysis records",
        )

        # Insert companies and get IDs
        logger.info("Inserting companies...")
        conn.execute(
            """
            INSERT INTO tracked_stocks (symbol, name, added_date, entity_id)
            SELECT symbol, name, added_date, entity_id
            FROM companies_df
        """,
        )

        if metrics_df is not None:
            logger.info("Inserting metrics...")
            # Join with tracked_stocks to get stock_id
            conn.execute(
                """
                INSERT INTO financial_metrics (
                    id, stock_id, metric_name, metric_namespace, value, unit,
                    start_date, end_date, filed_date, form, frame
                )
                SELECT
                    nextval('financial_metrics_id_seq'),
                    ts.id,
                    m.metric_name,
                    m.metric_namespace,
                    m.value,
                    m.unit,
                    m.start_date,
                    m.end_date,
                    m.filed_date,
                    m.form,
                    m.frame
                FROM metrics_df m
                JOIN tracked_stocks ts ON m.symbol = ts.symbol
            """,
            )

        if analysis_df is not None:
            logger.info("Inserting analysis...")
            # Join with tracked_stocks to get stock_id
            conn.execute(
                """
                INSERT INTO stock_analysis (
                    id, stock_id, timestamp, market_cap, pe_ratio,
                    fundamental_changes, market_insights
                )
                SELECT
                    nextval('stock_analysis_id_seq'),
                    ts.id,
                    a.timestamp,
                    a.market_cap,
                    a.pe_ratio,
                    a.fundamental_changes,
                    a.market_insights
                FROM analysis_df a
                JOIN tracked_stocks ts ON a.symbol = ts.symbol
            """,
            )

        # Commit after batch
        logger.info("Committing batch...")
        conn.commit()
        logger.info("Batch processed successfully")

        # Sync to MotherDuck if available
        if md_conn:
            logger.info("Syncing to MotherDuck...")
            _process_batch(md_conn, None, companies, metrics, analysis)

    except Exception as e:
        logger.exception(f"Error processing batch: {e!s}")
        logger.exception(f"Companies in batch: {[c['symbol'] for c in companies]}")
        conn.rollback()
        raise


def get_most_recent_filing_date(data):
    """Get the most recent filing date from company data."""
    most_recent = None
    facts = data.get("facts", {})

    # Check both US GAAP and DEI facts
    for namespace in ["us-gaap", "dei"]:
        namespace_data = facts.get(namespace, {})
        for metric_data in namespace_data.values():
            for unit_values in metric_data.get("units", {}).values():
                for value in unit_values:
                    filed_date = value.get("filed")
                    if filed_date and (not most_recent or filed_date > most_recent):
                        most_recent = filed_date

    return most_recent


def get_latest_financial_metrics(data):
    """Extract the latest financial metrics from company data."""
    metrics = {}
    facts = data.get("facts", {})

    # Process both US GAAP and DEI metrics
    for namespace in ["us-gaap", "dei"]:
        namespace_data = facts.get(namespace, {})
        for metric_name, metric_data in namespace_data.items():
            units = metric_data.get("units", {})
            for unit_type, values in units.items():
                # Get the most recent value
                if not values:
                    continue

                latest_value = max(values, key=lambda x: x.get("end", ""))

                metrics[metric_name] = {
                    "value": latest_value.get("val"),
                    "unit": unit_type,
                    "start_date": latest_value.get("start"),
                    "end_date": latest_value.get("end"),
                    "form": latest_value.get("form"),
                    "frame": latest_value.get("frame"),
                    "namespace": namespace,
                }
                break  # Only take the first unit type

    return metrics


def main() -> None:
    """Main execution function."""
    try:
        # Get database connections
        local_conn, md_conn = get_db_connections()

        # Process company files
        process_company_files(local_conn, md_conn)

        # Close connections
        local_conn.close()
        if md_conn:
            md_conn.close()

        logger.info("Successfully integrated SEC company facts")
    except Exception as e:
        logger.exception(f"Failed to process SEC company facts: {e}")
        raise


if __name__ == "__main__":
    main()
