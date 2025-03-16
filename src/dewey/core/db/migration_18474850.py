# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Migration script to move data from SQLite to DuckDB.

This script handles the one-time migration of data from the SQLite database to DuckDB.
"""

import os

from .duckdb_store import WORKSPACE_ROOT, migrate_from_sqlite


def main() -> None:
    """Run the migration from SQLite to DuckDB."""
    # Get the path to the SQLite database
    sqlite_path = WORKSPACE_ROOT / "data" / "research.db"

    if not sqlite_path.exists():
        return

    # Create a backup of the SQLite database
    backup_path = sqlite_path.with_suffix(".db.bak")
    if not backup_path.exists():
        os.system(f"cp {sqlite_path} {backup_path}")

    try:
        migrate_from_sqlite(str(sqlite_path))

    except Exception:
        os.system(f"cp {backup_path} {sqlite_path}")
        raise


if __name__ == "__main__":
    main()
