
# Refactored from: inspect_db
# Date: 2025-03-16T16:19:10.625698
# Refactor Version: 1.0
```python
import duckdb
import os
from pathlib import Path
from typing import List, Optional, Tuple


def find_database_path() -> Optional[Path]:
    """Locates the database file in several possible locations.

    Returns:
        Path: The path to the database if found, otherwise None.
    """
    possible_paths = [
        Path("research_results/research.db"),
        Path("jupyter/research/research_results/research.db"),
        Path(os.path.expanduser("~/notebooks/research_results/research.db")),
        Path(
            os.path.expanduser(
                "~/notebooks/jupyter/research/research_results/research.db"
            )
        ),
        Path.cwd() / "research_results" / "research.db",
    ]

    for path in possible_paths:
        if path.exists():
            print(f"Found database at {path}")
            return path

    print("Could not find research.db in any expected location")
    return None


def list_tables(con: duckdb.DuckDBPyConnection) -> List[Tuple[str]]:
    """Lists all tables in the database.

    Args:
        con: The DuckDB connection object.

    Returns:
        A list of tuples, where each tuple contains the table name.
    """
    print("\nTables in database:")
    tables = con.execute("SHOW TABLES").fetchall()
    print(tables)
    return tables


def inspect_table(con: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """Inspects a single table, printing its schema and first few rows.

    Args:
        con: The DuckDB connection object.
        table_name: The name of the table to inspect.
    """
    print(f"\nSchema for {table_name}:")
    schema = con.execute(f"DESCRIBE {table_name}").fetchall()
    for col in schema:
        print(col)

    print(f"\nFirst few rows of {table_name}:")
    rows = con.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
    for row in rows:
        print(row)


def inspect_db() -> None:
    """Inspects a DuckDB database, listing tables and their schemas."""
    db_path = find_database_path()

    if not db_path:
        return

    con: Optional[duckdb.DuckDBPyConnection] = None  # Initialize con to None
    try:
        # Connect to the database
        con = duckdb.connect(str(db_path))

        # List all tables
        tables = list_tables(con)

        if tables:
            for table in tables:
                table_name = table[0]
                inspect_table(con, table_name)
        else:
            print("No tables found in database")

    except Exception as e:
        print(f"Error inspecting database: {e}")
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    inspect_db()
```
