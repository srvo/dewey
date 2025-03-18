
# Refactored from: merge_data
# Date: 2025-03-16T16:19:11.637649
# Refactor Version: 1.0
# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

from pathlib import Path

import duckdb


def merge_podcast_data() -> None:
    """Merge podcast data into the research database."""
    workspace_root = Path(__file__).parent.parent
    podcast_db_path = workspace_root / "data" / "podcast_data.duckdb"
    research_db_path = workspace_root / "data" / "research.duckdb"

    # Connect to research database
    research_conn = duckdb.connect(str(research_db_path))

    try:
        # Start transaction
        research_conn.execute("BEGIN TRANSACTION")

        # Attach podcast database
        research_conn.execute(f"ATTACH '{podcast_db_path!s}' AS podcast_db")

        # Get list of tables from podcast database that actually exist
        tables = research_conn.execute(
            """
            SELECT DISTINCT table_name
            FROM podcast_db.information_schema.tables t
            WHERE table_schema = 'main'
            AND EXISTS (
                SELECT 1
                FROM podcast_db.information_schema.columns c
                WHERE c.table_name = t.table_name
                AND c.table_schema = 'main'
            )
        """,
        ).fetchall()

        # Copy each table to research database
        for (table_name,) in tables:
            try:

                # Test if table exists and has data
                test = research_conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM podcast_db.main.{table_name}
                    LIMIT 1
                """,
                ).fetchone()

                if test is None:
                    continue

                # Drop existing table if it exists
                research_conn.execute(f"DROP TABLE IF EXISTS {table_name}")

                # Create new table as copy
                research_conn.execute(
                    f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM podcast_db.main.{table_name}
                """,
                )

                # Get row count
                research_conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}",
                ).fetchone()[0]

            except Exception:
                continue

        # Commit transaction
        research_conn.execute("COMMIT")

    except Exception:
        research_conn.execute("ROLLBACK")
        raise

    finally:
        research_conn.close()


if __name__ == "__main__":
    merge_podcast_data()
