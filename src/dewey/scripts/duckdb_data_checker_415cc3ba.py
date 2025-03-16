# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Script to check data in DuckDB tables."""

from .duckdb_store import get_connection


def main() -> None:
    """Check data in DuckDB tables."""
    with get_connection() as conn:
        # Get list of all tables
        tables = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """,
        ).fetchall()

        for (table_name,) in tables:
            # Get record count
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            if count > 0:
                # Show sample data
                results = conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
                for _row in results:
                    pass


if __name__ == "__main__":
    main()
