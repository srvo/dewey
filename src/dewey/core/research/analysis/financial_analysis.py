# Refactored from: financial_analysis
# Date: 2025-03-16T16:19:10.702032
# Refactor Version: 1.0
#!/usr/bin/env python3
from datetime import datetime, timedelta
from typing import Any, Dict, List

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection


class FinancialAnalysis(BaseScript):
    """
    Analyzes financial data to identify significant changes and material events for a given set of stocks.
    """

    def __init__(self):
        """
        Initializes the FinancialAnalysis script with necessary configurations and connections.
        """
        super().__init__(
            name="Financial Analysis",
            description="Analyzes financial data for significant changes and material events.",
            config_section="financial_analysis",
            requires_db=True,
            enable_llm=False,
        )

    def sync_current_universe(self, local_conn: DatabaseConnection, md_conn: DatabaseConnection) -> None:
        """Sync current universe from MotherDuck to local DuckDB.

        Args:
            local_conn: Connection to the local DuckDB database.
            md_conn: Connection to the MotherDuck database.

        Returns:
            None

        Raises:
            Exception: If connection to MotherDuck fails.
        """
        if not md_conn:
            self.logger.warning("No MotherDuck connection available, skipping sync")
            return

        try:
            # Get current universe from MotherDuck
            stocks = md_conn.execute(
                """
                SELECT
                    ticker, security_name as name, COALESCE(sector, category, 'Unknown') as sector, COALESCE(category, sector, 'Unknown') as industry
                FROM current_universe
                WHERE ticker IS NOT NULL
                    AND security_name IS NOT NULL
                    AND workflow IS NOT NULL  -- Only include stocks with a workflow
                    AND workflow != 'excluded'  -- Exclude explicitly excluded stocks
                    AND workflow != 'ignore'  -- Exclude ignored stocks
            """, ).fetchdf()

            # Create and populate table in local DuckDB
            local_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS current_universe (
                    ticker VARCHAR PRIMARY KEY, name VARCHAR, sector VARCHAR, industry VARCHAR
                )
            """, )

            # Clear existing data
            local_conn.execute("DELETE FROM current_universe")

            # Insert new data
            local_conn.execute("INSERT INTO current_universe SELECT * FROM stocks")
            local_conn.commit()

            self.logger.info(f"Synced {len(stocks)} stocks to current_universe table")

        except Exception as e:
            self.logger.exception(f"Error syncing current universe: {e}")
            raise

    def get_current_universe(self) -> List[Dict[str, str]]:
        """Get the current universe of stocks.

        Returns:
            A list of dictionaries, each representing a stock with ticker, name, sector, and industry.

        Raises:
            Exception: If database query fails.
        """
        try:
            with get_connection() as conn:
                stocks_df = conn.execute(
                    """
                    -- Get stocks from current universe and join with tracked_stocks to get their IDs
                    SELECT DISTINCT
                        cu.ticker, cu.name, cu.sector, cu.industry
                    FROM current_universe cu
                    JOIN tracked_stocks ts ON
                        -- Match either direct symbol or CIK-based symbol
                        ts.symbol = cu.ticker
                        OR ts.entity_id = REPLACE(ts.symbol, 'C', '')
                    ORDER BY cu.sector, cu.industry, cu.ticker
                    """, ).fetchdf()

                stocks=None, row in stocks_df.iterrows():
                    if ).fetchdf()

                stocks is None:
                        ).fetchdf()

                stocks = []
                for _
                    stocks.append(
                        {
                            "ticker": row["ticker"],
                            "name": row["name"],
                            "sector": row["sector"],
                            "industry": row["industry"],
                        },
                    )

                return stocks
        except Exception as e:
            self.logger.exception(f"Error getting current universe: {e}")
            raise

    def analyze_financial_changes(self, ticker: str) -> List[Dict[str, Any]]:
        """Analyze significant financial metric changes for a given ticker.

        Args:
            ticker: The stock ticker to analyze.

        Returns:
            A list of dictionaries, each representing a significant financial metric change.

        Raises:
            Exception: If database query fails.
        """
        try:
            # Get the last 2 months of financial metrics
            two_months_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

            with get_connection() as conn:
                metrics = conn.execute(
                    """
                    WITH MetricChanges AS (
                        SELECT
                            metric_name, value as current_value, LAG(value) OVER (PARTITION BY metric_name ORDER BY end_date) as prev_value, end_date, filed_date
                        FROM financial_metrics fm
                        JOIN tracked_stocks ts ON fm.stock_id = ts.id
                        JOIN current_universe cu ON
                            -- Match either direct symbol or CIK-based symbol
                            (ts.symbol = cu.ticker OR ts.entity_id = REPLACE(ts.symbol, 'C', ''))
                        WHERE cu.ticker = ?
                            AND end_date >= ?
                            AND metric_namespace = 'us-gaap'
                            AND metric_name IN (
                                'Assets', 'Liabilities', 'Revenues', 'NetIncomeLoss', 'OperatingIncomeLoss', 'StockholdersEquity', 'CashAndCashEquivalentsAtCarryingValue'
                            )
                        ORDER BY end_date DESC
                    )
                    SELECT
                        metric_name, current_value, prev_value, end_date, filed_date, CASE
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
                    """, [ticker, two_months_ago], ).fetchdf()

                return metrics.to_dict("records") if not metrics.empty else []
        except Exception as e:
            self.logger.exception(f"Error analyzing financial changes for {ticker}: {e}")
            raise

    def analyze_material_events(self, ticker: str) -> List[str]:
        """Analyze material events from SEC filings for a given ticker.

        Args:
            ticker: The stock ticker to analyze.

        Returns:
            A list of strings, each representing a material event.

        Raises:
            Exception: If database query fails.
        """
        try:
            # Get recent filings
            two_months_ago=None, )
                else:
                    events.append(
                        f"Significant change in {metric}: {'increased' if pct_change > 0 else 'decreased'} by {pct_change:.1f}% as of {date}", )

            # Look for specific material events in filings
            with get_connection() as conn:
                material_events = conn.execute(
                    """
                    SELECT DISTINCT
                        form, filed_date, metric_name, value, start_date, end_date
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
                    """, [ticker, two_months_ago], ).fetchdf()

                if not material_events.empty:
                    for _, event in material_events.iterrows():
                        if each representing a material event.

        Raises:
            Exception: If database query fails.
        """
        try:
            # Get recent filings
            two_months_ago is None:
                            each representing a material event.

        Raises:
            Exception: If database query fails.
        """
        try:
            # Get recent filings
            two_months_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

            events = []

            # Look for significant events in financial metrics
            changes = self.analyze_financial_changes(ticker)
            for change in changes:
                metric = change["metric_name"]
                pct_change = change["pct_change"]
                date = change["end_date"].strftime("%Y-%m-%d")

                if abs(pct_change) > 50:  # Very significant change
                    events.append(
                        f"MAJOR CHANGE: {metric} {'increased' if pct_change > 0 else 'decreased'} by {pct_change:.1f}% as of {date}"
                        events.append(
                            f"Material event ({event['form']} filed {event['filed_date'].strftime('%Y-%m-%d')}): {event['metric_name']}",
                        )

                return events
        except Exception as e:
            self.logger.exception(f"Error analyzing material events for {ticker}: {e}")
            raise

    def run(self) -> None:
        """
        Executes the financial analysis process.

        This includes:
        1. Retrieving the current universe of stocks.
        2. Analyzing each stock for material events.
        3. Printing a summary of material findings.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any part of the analysis fails.
        """
        try:
            # Get current universe
            stocks=None, )

                events = self.analyze_material_events(ticker)
                if events:
                    material_findings.append(
                        {
                            "ticker": ticker, "name": stock["name"], "sector": stock["sector"], "industry": stock["industry"], "events": events, }, )

            # Print summary of material findings
            if material_findings:
                # Group by sector
                by_sector=None, findings in by_sector.items():
                    if self) -> None:
        """
        Executes the financial analysis process.

        This includes:
        1. Retrieving the current universe of stocks.
        2. Analyzing each stock for material events.
        3. Printing a summary of material findings.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any part of the analysis fails.
        """
        try:
            # Get current universe
            stocks is None:
                        self) -> None:
        """
        Executes the financial analysis process.

        This includes:
        1. Retrieving the current universe of stocks.
        2. Analyzing each stock for material events.
        3. Printing a summary of material findings.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any part of the analysis fails.
        """
        try:
            # Get current universe
            stocks = self.get_current_universe()
            self.logger.info(f"Found {len(stocks)} stocks in current universe")

            # Analyze each stock
            material_findings = []

            for stock in stocks:
                ticker = stock["ticker"]
                self.logger.info(
                    f"\nAnalyzing {ticker} ({stock['name']}) - {stock['sector']}/{stock['industry']}..."
                    if )

            # Print summary of material findings
            if material_findings:
                # Group by sector
                by_sector is None:
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
                for sector
                    for finding in findings:
                        for event in finding["events"]:
                            self.logger.info(f"{finding['ticker']} ({sector}): {event}")
            else:
                self.logger.info("No material findings to report")

            self.logger.info("\nAnalysis completed successfully")

        except Exception as e:
            self.logger.exception(f"Error during analysis: {e!s}")
            raise


def main() -> None:
    """
    Main entry point for the financial analysis script.
    """
    analysis = FinancialAnalysis()
    analysis.execute()


if __name__ == "__main__":
    main()
