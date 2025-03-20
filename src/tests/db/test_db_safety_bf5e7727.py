# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Test script for database safety features."""

from ethifinx.db.duckdb_store import get_connection


def test_safety() -> None:
    """Test the safety confirmation for destructive operations."""
    with get_connection() as conn:
        # Try a destructive operation
        conn.execute("DROP TABLE IF EXISTS test_table")

        # Try a safe operation
        conn.execute("SELECT COUNT(*) FROM research_sources")


if __name__ == "__main__":
    test_safety()
