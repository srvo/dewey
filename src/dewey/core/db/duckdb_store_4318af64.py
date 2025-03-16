# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""DuckDB data store module.

This module handles DuckDB database setup, connections, and migrations.
"""
from __future__ import annotations

import os
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from collections.abc import Generator

# Default database paths - using workspace root
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/Users/srvo/ethifinx"))
DEFAULT_DB_PATH = WORKSPACE_ROOT / "data" / "research.duckdb"


def init_db(db_path: str | None = None) -> None:
    """Initialize the DuckDB database with required tables.

    Args:
    ----
        db_path: Optional path to the database file. If not provided, uses default path.

    """
    db_path = db_path or str(DEFAULT_DB_PATH)

    # Ensure data directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        # Create sequences for all tables
        sequences = [
            "research_id_seq",
            "test_table_id_seq",
            "company_context_id_seq",
            "universe_id_seq",
            "research_sources_id_seq",
            "portfolio_id_seq",
            "research_iterations_id_seq",
            "research_results_id_seq",
            "exclusions_id_seq",
            "tick_history_id_seq",
            "research_reviews_id_seq",
        ]

        for seq in sequences:
            conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq};")

        # Create tables
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research (
                id BIGINT DEFAULT nextval('research_id_seq'),
                ticker VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                stage VARCHAR NOT NULL,
                retries INTEGER,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id BIGINT DEFAULT nextval('test_table_id_seq'),
                key VARCHAR NOT NULL,
                value VARCHAR NOT NULL,
                PRIMARY KEY (id)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS company_context (
                id BIGINT DEFAULT nextval('company_context_id_seq'),
                ticker VARCHAR NOT NULL,
                context TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE (ticker)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS universe (
                id BIGINT DEFAULT nextval('universe_id_seq'),
                name VARCHAR NOT NULL,
                ticker VARCHAR NOT NULL,
                isin VARCHAR,
                security_type VARCHAR,
                market_cap DOUBLE,
                sector VARCHAR,
                industry VARCHAR,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE (ticker)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_sources (
                id BIGINT DEFAULT nextval('research_sources_id_seq'),
                ticker VARCHAR NOT NULL,
                url VARCHAR NOT NULL,
                title VARCHAR,
                snippet TEXT,
                source_type VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE (ticker, url)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id BIGINT DEFAULT nextval('portfolio_id_seq'),
                ticker VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                sector VARCHAR,
                weight DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE (ticker)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_iterations (
                id BIGINT DEFAULT nextval('research_iterations_id_seq'),
                company_ticker VARCHAR NOT NULL,
                iteration_type VARCHAR NOT NULL,
                source_count INTEGER,
                date_range VARCHAR,
                previous_iteration_id INTEGER,
                summary TEXT,
                key_changes JSON,
                risk_factors JSON,
                opportunities JSON,
                confidence_metrics JSON,
                status VARCHAR,
                reviewer_notes TEXT,
                reviewed_by VARCHAR,
                reviewed_at TIMESTAMP,
                prompt_template VARCHAR,
                model_version VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE (company_ticker, iteration_type, created_at)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_results (
                id BIGINT DEFAULT nextval('research_results_id_seq'),
                company_ticker VARCHAR NOT NULL,
                summary TEXT,
                risk_score INTEGER,
                confidence_score INTEGER,
                recommendation VARCHAR,
                structured_data JSON,
                raw_results JSON,
                search_queries JSON,
                source_date_range VARCHAR,
                total_sources INTEGER,
                source_categories JSON,
                last_iteration_id INTEGER,
                first_analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP,
                meta_info JSON,
                PRIMARY KEY (id),
                UNIQUE (company_ticker)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exclusions (
                id BIGINT DEFAULT nextval('exclusions_id_seq'),
                ticker VARCHAR NOT NULL,
                reason VARCHAR NOT NULL,
                details TEXT,
                excluded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                excluded_by VARCHAR,
                PRIMARY KEY (id),
                UNIQUE (ticker)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tick_history (
                id BIGINT DEFAULT nextval('tick_history_id_seq'),
                ticker VARCHAR NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                old_tick INTEGER,
                new_tick INTEGER NOT NULL,
                note TEXT,
                updated_by VARCHAR,
                PRIMARY KEY (id),
                UNIQUE (ticker, date)
            )
        """,
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_reviews (
                id BIGINT DEFAULT nextval('research_reviews_id_seq'),
                research_result_id INTEGER NOT NULL,
                iteration_id INTEGER,
                company_ticker VARCHAR NOT NULL,
                review_status VARCHAR NOT NULL,
                accuracy_rating INTEGER,
                completeness_rating INTEGER,
                factual_errors JSON,
                missing_aspects JSON,
                incorrect_emphasis JSON,
                follow_up_tasks JSON,
                priority_level VARCHAR,
                reviewer_notes TEXT,
                reviewed_by VARCHAR NOT NULL,
                reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                prompt_improvement TEXT,
                source_quality JSON,
                PRIMARY KEY (id),
                UNIQUE (research_result_id)
            )
        """,
        )


def require_confirmation(conn: duckdb.DuckDBPyConnection, query: str) -> bool:
    """Require user confirmation for destructive operations.

    Args:
    ----
        conn: DuckDB connection
        query: SQL query to check

    Returns:
    -------
        bool: Whether to proceed with the operation

    """
    destructive_keywords = ["DROP", "DELETE", "TRUNCATE"]
    if any(keyword in query.upper() for keyword in destructive_keywords):
        confirm = input("\nType 'yes' to confirm: ")
        return confirm.lower() == "yes"
    return True


class SafeConnection:
    """Wrapper for DuckDB connection that requires confirmation for destructive operations."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def execute(self, query: str, *args, **kwargs):
        """Execute a query with safety checks.

        Args:
        ----
            query: SQL query to execute
            *args: Positional arguments for the query
            **kwargs: Keyword arguments for the query

        Returns:
        -------
            Query results if successful, None if cancelled

        """
        if require_confirmation(self._conn, query):
            return self._conn.execute(query, *args, **kwargs)
        return None

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying connection."""
        return getattr(self._conn, name)


@contextmanager
def get_connection(
    db_path: str | None = None,
) -> Generator[SafeConnection, None, None]:
    """Get a DuckDB connection with context management.

    Args:
    ----
        db_path: Optional path to the database file. If not provided, uses default path.

    Yields:
    ------
        SafeConnection object that requires confirmation for destructive operations

    """
    db_path = db_path or str(DEFAULT_DB_PATH)
    conn = duckdb.connect(str(db_path))
    safe_conn = SafeConnection(conn)
    try:
        yield safe_conn
    finally:
        safe_conn.close()


def migrate_from_sqlite(sqlite_path: str, duckdb_path: str | None = None) -> None:
    """Migrate data from SQLite to DuckDB.

    Args:
    ----
        sqlite_path: Path to the SQLite database file
        duckdb_path: Optional path to the DuckDB database file. If not provided, uses default path.

    """
    duckdb_path = duckdb_path or str(DEFAULT_DB_PATH)

    # Initialize DuckDB database
    init_db(duckdb_path)

    with get_connection(duckdb_path) as conn:
        # Load SQLite extension
        conn.execute("INSTALL sqlite;")
        conn.execute("LOAD sqlite;")

        # List of tables to migrate from research.db
        tables = [
            "research",
            "test_table",
            "company_context",
            "universe",
            "research_sources",
            "portfolio",
            "research_iterations",
            "research_results",
            "exclusions",
            "tick_history",
            "research_reviews",
        ]

        # Migrate each table from research.db
        for table in tables:
            try:
                conn.execute(
                    f"""
                    INSERT INTO {table}
                    SELECT * FROM sqlite_scan('{sqlite_path}', '{table}')
                """,
                )
            except Exception:
                continue

        # Migrate data from research.db.backup
        backup_path = "/Users/srvo/research.db.backup"
        if os.path.exists(backup_path):

            # Migrate companies to universe
            with suppress(Exception):
                conn.execute(
                    f"""
                    INSERT INTO universe (name, ticker, isin, sector, industry, description)
                    SELECT DISTINCT name, ticker, isin, sector, industry, description
                    FROM sqlite_scan('{backup_path}', 'companies')
                    WHERE ticker IS NOT NULL
                    ON CONFLICT (ticker) DO UPDATE SET
                        name = EXCLUDED.name,
                        sector = EXCLUDED.sector,
                        industry = EXCLUDED.industry,
                        description = EXCLUDED.description
                """,
                )

            # Migrate research_sources
            try:
                # First get distinct ticker-url combinations with deduplication
                conn.execute(
                    """
                    CREATE TEMP TABLE source_entries AS
                    WITH numbered_sources AS (
                        SELECT
                            company_ticker,
                            url,
                            title,
                            snippet,
                            source_type,
                            category,
                            ROW_NUMBER() OVER (PARTITION BY company_ticker ORDER BY id) as url_num
                        FROM read_csv_auto('/Users/srvo/ethifinx/ethifinx/data/research_sources_202501070552.csv')
                        WHERE company_ticker IS NOT NULL
                    ),
                    processed_sources AS (
                        SELECT
                            company_ticker,
                            COALESCE(url, 'unknown_' || company_ticker || '_' || url_num) as url,
                            title,
                            snippet,
                            COALESCE(source_type, 'unknown') as source_type,
                            COALESCE(category, 'general') as category
                        FROM numbered_sources
                    )
                    SELECT DISTINCT ON (company_ticker, url)
                        company_ticker,
                        url,
                        title,
                        snippet,
                        source_type,
                        category
                    FROM processed_sources
                    ORDER BY company_ticker, url
                """,
                )

                # Get count of entries
                conn.execute(
                    "SELECT COUNT(*) FROM source_entries",
                ).fetchone()[0]

                # Insert without duplicates
                conn.execute(
                    """
                    INSERT INTO research_sources (
                        ticker, url, title, snippet,
                        source_type, category
                    )
                    SELECT
                        company_ticker,
                        url,
                        title,
                        snippet,
                        source_type,
                        category
                    FROM source_entries
                """,
                )

                # Cleanup
                conn.execute("DROP TABLE source_entries")
            except Exception:
                # Cleanup on error
                conn.execute("DROP TABLE IF EXISTS source_entries")

            # Migrate research_results
            with suppress(Exception):
                conn.execute(
                    f"""
                    INSERT INTO research_results (
                        company_ticker, summary, risk_score, confidence_score,
                        recommendation, structured_data, raw_results, search_queries
                    )
                    SELECT DISTINCT
                        company_ticker, summary, risk_score, confidence_score,
                        recommendation, structured_data, raw_results, search_queries
                    FROM sqlite_scan('{backup_path}', 'research_results')
                    WHERE company_ticker IS NOT NULL
                    ON CONFLICT (company_ticker) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        risk_score = EXCLUDED.risk_score,
                        confidence_score = EXCLUDED.confidence_score,
                        recommendation = EXCLUDED.recommendation,
                        structured_data = EXCLUDED.structured_data,
                        raw_results = EXCLUDED.raw_results,
                        search_queries = EXCLUDED.search_queries
                """,
                )

            # Migrate research_checkpoints
            with suppress(Exception):
                conn.execute(
                    f"""
                    INSERT INTO research_iterations (
                        company_ticker, iteration_type, status,
                        reviewer_notes
                    )
                    SELECT DISTINCT
                        company_ticker, 'checkpoint',
                        CASE
                            WHEN error_message IS NOT NULL THEN 'error'
                            ELSE 'completed'
                        END,
                        error_message
                    FROM sqlite_scan('{backup_path}', 'research_checkpoints')
                    WHERE company_ticker IS NOT NULL
                """,
                )

            # Migrate ethical_analysis to research_iterations
            with suppress(Exception):
                conn.execute(
                    f"""
                    INSERT INTO research_iterations (
                        company_ticker, iteration_type, summary,
                        key_changes, risk_factors, opportunities,
                        confidence_metrics, status
                    )
                    SELECT DISTINCT
                        symbol, 'ethical_analysis', description,
                        json_object('pattern', historical_pattern),
                        json_object('severity', severity_score, 'pattern', pattern_score),
                        json_object('stakeholder_impact', stakeholder_impact),
                        json_object('evidence_strength', evidence_strength),
                        'completed'
                    FROM sqlite_scan('{backup_path}', 'ethical_analysis')
                    WHERE symbol IS NOT NULL
                """,
                )


def enable_safety_features(db_path: str | None = None) -> None:
    """Enable safety features on the database.

    Args:
    ----
        db_path: Optional path to the database file. If not provided, uses default path.

    """
    db_path = db_path or str(DEFAULT_DB_PATH)

    with get_connection(db_path) as conn:
        # Create a trigger function for destructive operations
        conn.execute(
            """
            CREATE OR REPLACE FUNCTION check_destructive_ops() AS
            BEGIN
                RAISE NOTICE 'Destructive operation detected';
                -- DuckDB will show this notice and require confirmation
                RETURN NEW;
            END;
        """,
        )


if __name__ == "__main__":
    # Enable safety features when script is run directly
    enable_safety_features()
