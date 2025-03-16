# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

import contextlib
from pathlib import Path

import duckdb


def merge_port_data() -> None:
    """Merge tick history data from port database into the research database."""
    workspace_root = Path(__file__).parent.parent
    port_db_path = workspace_root / "data" / "port.duckdb"
    research_db_path = workspace_root / "data" / "research.duckdb"

    # Connect to research database
    research_conn = duckdb.connect(str(research_db_path))

    try:
        # Start transaction
        research_conn.execute("BEGIN TRANSACTION")

        # Attach port database
        research_conn.execute(f"ATTACH '{port_db_path!s}' AS port_db")

        # First check if the table exists
        table_exists = research_conn.execute(
            """
            SELECT COUNT(*)
            FROM port_db.information_schema.tables
            WHERE table_name = 'tick_history'
            AND table_schema = 'main'
        """,
        ).fetchone()[0]

        if not table_exists:
            research_conn.execute("ROLLBACK")
            return

        # Get column information
        columns = research_conn.execute(
            """
            SELECT column_name, data_type
            FROM port_db.information_schema.columns
            WHERE table_name = 'tick_history'
            AND table_schema = 'main'
            ORDER BY ordinal_position
        """,
        ).fetchall()

        for _col, _dtype in columns:
            pass

        # Create the table in research database if it doesn't exist
        columns_sql = ", ".join([f"{col} {dtype}" for col, dtype in columns])
        research_conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS tick_history (
                {columns_sql}
            )
        """,
        )

        # Create backup of existing data
        research_conn.execute(
            """
            CREATE TABLE tick_history_backup AS
            SELECT * FROM tick_history
        """,
        )

        # Get the latest entry date for each ticker in research database
        research_conn.execute(
            """
            CREATE TEMP TABLE latest_entries AS
            SELECT ticker, MAX(date) as last_date
            FROM tick_history
            GROUP BY ticker
        """,
        )

        # Insert only newer entries from port database
        inserted = research_conn.execute(
            """
            WITH to_insert AS (
                SELECT p.*
                FROM port_db.tick_history p
                LEFT JOIN latest_entries l ON p.ticker = l.ticker
                WHERE l.last_date IS NULL  -- New tickers
                   OR p.date > l.last_date -- Newer entries
            )
            INSERT INTO tick_history
            SELECT * FROM to_insert
            RETURNING COUNT(*)
        """,
        ).fetchone()[0]

        if inserted == 0:
            research_conn.execute("ROLLBACK")
            return

        # Sample of new data
        sample = research_conn.execute(
            """
            SELECT * FROM tick_history
            WHERE NOT EXISTS (
                SELECT 1 FROM tick_history_backup b
                WHERE b.ticker = tick_history.ticker
                AND b.date = tick_history.date
            )
            LIMIT 5
        """,
        ).fetchall()
        for _row in sample:
            pass

        # Drop backup and temp tables
        research_conn.execute("DROP TABLE tick_history_backup")
        research_conn.execute("DROP TABLE latest_entries")

        # Commit transaction
        research_conn.execute("COMMIT")

    except Exception:
        research_conn.execute("ROLLBACK")
        # If there was an error, restore from backup if it exists
        with contextlib.suppress(Exception):
            research_conn.execute(
                """
                DROP TABLE IF EXISTS tick_history;
                ALTER TABLE tick_history_backup RENAME TO tick_history;
            """,
            )
        raise

    finally:
        research_conn.close()


if __name__ == "__main__":
    merge_port_data()
