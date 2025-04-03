#!/usr/bin/env python
"""Direct sync from MotherDuck to local DuckDB.
This script bypasses the normal sync mechanism and directly copies tables
using SQL statements.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import duckdb


def main():
    """Directly sync tables from MotherDuck to local DuckDB."""
    # Get MotherDuck token from environment
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token:
        print("Error: MOTHERDUCK_TOKEN environment variable is not set")
        return 1

    # Set up paths
    local_db_path = str(project_root / "dewey.duckdb")
    motherduck_db = "dewey"

    print(f"Syncing from MotherDuck:{motherduck_db} to local:{local_db_path}")

    try:
        # Connect to both databases
        md_conn = duckdb.connect(f"md:{motherduck_db}?motherduck_token={token}")
        local_conn = duckdb.connect(local_db_path)

        # Create a temporary directory for CSV files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get list of tables from MotherDuck
            tables = md_conn.execute("SHOW TABLES").fetchall()
            table_names = [table[0] for table in tables]

            # Filter out system tables
            tables_to_sync = [
                t
                for t in table_names
                if not t.startswith("sqlite_")
                and not t.startswith("dewey_sync_")
                and not t.startswith("information_schema")
            ]

            print(f"Found {len(tables_to_sync)} tables to sync")

            # Sync each table
            synced_tables = 0
            for table_name in tables_to_sync:
                print(f"Syncing table: {table_name}")
                start_time = time.time()

                try:
                    # Count rows in the source table
                    row_count = md_conn.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    print(f"  Source has {row_count} rows")

                    # Skip if table is empty
                    if row_count == 0:
                        print(f"  Table {table_name} is empty, skipping")
                        continue

                    # Step 1: Get schema from MotherDuck
                    schema_result = md_conn.execute(f"DESCRIBE {table_name}").fetchall()
                    columns = []
                    create_stmt_parts = []

                    for col in schema_result:
                        col_name = col[0]
                        col_type = col[1]
                        columns.append(col_name)
                        create_stmt_parts.append(f'"{col_name}" {col_type}')

                    create_stmt = (
                        f"CREATE TABLE {table_name} ({', '.join(create_stmt_parts)})"
                    )

                    # Step 2: Export from MotherDuck to CSV
                    csv_path = os.path.join(temp_dir, f"{table_name}.csv")
                    md_conn.execute(
                        f"COPY (SELECT * FROM {table_name}) TO '{csv_path}' (HEADER, DELIMITER ',')"
                    )

                    # Step 3: Create table in local and import from CSV
                    local_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                    local_conn.execute(create_stmt)
                    local_conn.execute(
                        f"COPY {table_name} FROM '{csv_path}' (HEADER, DELIMITER ',')"
                    )

                    # Verify row count in the destination
                    local_rows = local_conn.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    print(f"  Destination has {local_rows} rows")

                    duration = time.time() - start_time
                    print(f"  Synced in {duration:.2f} seconds")
                    synced_tables += 1
                except Exception as e:
                    print(f"  Error syncing {table_name}: {e}")

            print(
                f"\nSummary: Successfully synced {synced_tables}/{len(tables_to_sync)} tables"
            )

            # Get the database file size
            db_size = Path(local_db_path).stat().st_size / (
                1024 * 1024
            )  # Convert to MB
            print(f"Local database size: {db_size:.2f} MB")

        # Close connections
        md_conn.close()
        local_conn.close()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
