#!/usr/bin/env python3

"""
Script to analyze tables in both local DuckDB and MotherDuck databases.
Provides information about table structure, row counts, and data samples.
"""

import json
import os
from datetime import datetime

import duckdb
from dotenv import load_dotenv


def format_table_info(table_name, row_count, schema, sample_row=None):
    """Format table information in a consistent way."""
    info = {
        "table_name": table_name,
        "row_count": row_count,
        "schema": schema,
        "sample_row": sample_row or None,
    }
    return info


def analyze_database(conn, db_name):
    """Analyze tables in a database connection."""
    results = []

    try:
        # Get list of tables
        tables = conn.execute("SHOW TABLES").fetchall()

        print(f"\n=== Database: {db_name} ===")
        print(f"Found {len(tables)} tables\n")

        for table in tables:
            table_name = table[0]
            try:
                # Get row count
                row_count = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}",
                ).fetchone()[0]

                # Get schema
                schema = conn.execute(f"DESCRIBE {table_name}").fetchall()
                schema_dict = {col[0]: col[1] for col in schema}

                # Get sample row if table has data
                sample_row = None
                if row_count > 0:
                    sample_row = conn.execute(
                        f"SELECT * FROM {table_name} LIMIT 1",
                    ).fetchone()
                    if sample_row:
                        sample_row = dict(
                            zip([col[0] for col in schema], sample_row, strict=False),
                        )

                table_info = format_table_info(
                    table_name, row_count, schema_dict, sample_row,
                )
                results.append(table_info)

                print(f"\nTable: {table_name}")
                print(f"Row count: {row_count}")
                print("Schema:")
                for col_name, col_type in schema_dict.items():
                    print(f"  {col_name}: {col_type}")
                if sample_row:
                    print("Sample row:")
                    for key, value in sample_row.items():
                        print(f"  {key}: {value}")

            except Exception as e:
                print(f"Error analyzing table {table_name}: {e!s}")
                continue

    except Exception as e:
        print(f"Error listing tables in {db_name}: {e!s}")

    return results


def analyze_tables():
    """Analyze tables in both local and MotherDuck databases."""
    results = {"timestamp": datetime.now().isoformat(), "databases": {}}

    # Load environment variables
    load_dotenv()

    # Check local database
    local_path = os.path.expanduser("~/dewey_emails.duckdb")
    if os.path.exists(local_path):
        try:
            local_conn = duckdb.connect(local_path)
            results["databases"]["local"] = analyze_database(local_conn, "Local DuckDB")
            local_conn.close()
        except Exception as e:
            print(f"Error connecting to local database: {e!s}")
    else:
        print("Local database not found")

    # Connect to MotherDuck
    try:
        md_conn = duckdb.connect("md:")

        # Switch to dewey database
        md_conn.execute("USE dewey")

        results["databases"]["motherduck"] = analyze_database(md_conn, "MotherDuck")
        md_conn.close()
    except Exception as e:
        print(f"Error connecting to MotherDuck: {e!s}")

    # Save results to file
    try:
        with open("table_analysis_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\nResults saved to table_analysis_results.json")
    except Exception as e:
        print(f"Error saving results: {e!s}")


if __name__ == "__main__":
    analyze_tables()
