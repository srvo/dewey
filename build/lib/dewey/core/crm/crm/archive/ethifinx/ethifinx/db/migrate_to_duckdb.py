"""Migration script to move data from SQLite to DuckDB.

This script handles the one-time migration of data from the SQLite database to DuckDB.
"""

import os
from pathlib import Path
from .duckdb_store import migrate_from_sqlite, WORKSPACE_ROOT

def main():
    """Run the migration from SQLite to DuckDB."""
    # Get the path to the SQLite database
    sqlite_path = WORKSPACE_ROOT / "data" / "research.db"
    
    if not sqlite_path.exists():
        print(f"SQLite database not found at {sqlite_path}")
        return
    
    # Create a backup of the SQLite database
    backup_path = sqlite_path.with_suffix('.db.bak')
    if not backup_path.exists():
        print(f"Creating backup of SQLite database at {backup_path}")
        os.system(f"cp {sqlite_path} {backup_path}")
    
    try:
        print("Starting migration to DuckDB...")
        migrate_from_sqlite(str(sqlite_path))
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        print("Rolling back to SQLite backup...")
        os.system(f"cp {backup_path} {sqlite_path}")
        raise

if __name__ == "__main__":
    main() 