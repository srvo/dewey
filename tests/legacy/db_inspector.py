
# Refactored from: db_inspector
# Date: 2025-03-16T16:19:10.739754
# Refactor Version: 1.0
```python
import duckdb
from pathlib import Path
from typing import List, Tuple, Any


def _get_port_db_path() -> Path:
    """Gets the path to the port.duckdb database."""
    workspace_root = Path(__file__).parent.parent
    return workspace_root / "data" / "port.duckdb"


def _fetch_table_metadata(conn: duckdb.DuckDBPyConnection) -> List[Tuple[str, str, int]]:
    """Fetches metadata for all tables in the database.

    Args:
        conn: The DuckDB connection object.

    Returns:
        A list of tuples, where each tuple contains the schema, table name, and
        a flag indicating whether the table has data.
    """
    tables = conn.execute(
        """
        SELECT
            table_schema,
            table_name,
            (
                SELECT COUNT(*)
                FROM (
                    SELECT * FROM main."${table_name}" LIMIT 1
                )
            ) as has_data
        FROM information_schema.tables
        WHERE table_schema IN ('main', 'public')
        ORDER BY table_schema, table_name
        """
    ).fetchall()
    return tables


def _fetch_sample_data(conn: duckdb.DuckDBPyConnection, table: str) -> List[Tuple[Any]]:
    """Fetches sample data from a table.

    Args:
        conn: The DuckDB connection object.
        table: The name of the table to fetch data from.

    Returns:
        A list of tuples, where each tuple represents a row of data.
    """
    sample = conn.execute(f"""
        SELECT * FROM "{table}" LIMIT 3
    """).fetchall()
    return sample


def list_tables() -> None:
    """Lists all tables in the port database, including sample data."""
    port_db_path = _get_port_db_path()

    # Connect to database
    conn = duckdb.connect(str(port_db_path))

    try:
        tables = _fetch_table_metadata(conn)

        print(f"\nTables in {port_db_path}:")
        print("-" * 50)
        for schema, table, has_data in tables:
            status = "with data" if has_data > 0 else "empty"
            print(f"{schema}.{table} ({status})")

            # Show sample data if table has content
            if has_data > 0:
                sample = _fetch_sample_data(conn, table)
                print("Sample data:")
                for row in sample:
                    print(f"  {row}")
                print()

    finally:
        conn.close()


if __name__ == "__main__":
    list_tables()
```
