```python
from pathlib import Path
from typing import Any, List, Tuple

import duckdb


def get_port_db_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Establishes a connection to the Port database.

    Args:
        db_path: The path to the Port database file.

    Returns:
        A DuckDB connection object to the Port database.
    """
    return duckdb.connect(str(db_path), read_only=True)


def get_table_names(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """Retrieves a list of table names from the given DuckDB connection.

    Args:
        conn: The DuckDB connection object.

    Returns:
        A list of table names.
    """
    tables = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
    """
    ).fetchall()
    return [table[0] for table in tables]


def get_table_schema(
    conn: duckdb.DuckDBPyConnection, table_name: str
) -> List[Tuple[str, str, str]]:
    """Retrieves the schema of a given table from the DuckDB connection.

    Args:
        conn: The DuckDB connection object.
        table_name: The name of the table to retrieve the schema for.

    Returns:
        A list of tuples representing the schema, where each tuple contains:
        (column_name, data_type, is_nullable).
    """
    table_schema = conn.execute(
        f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
    """
    ).fetchall()
    return table_schema


def get_sample_data(conn: duckdb.DuckDBPyConnection, table_name: str) -> List[Tuple[Any]]:
    """Retrieves sample data from a given table.

    Args:
        conn: The DuckDB connection object.
        table_name: The name of the table to retrieve sample data from.

    Returns:
        A list of tuples representing the sample data.
    """
    sample = conn.execute(
        f"""
        SELECT *
        FROM "{table_name}"
        LIMIT 1
    """
    ).fetchall()
    return sample


def print_table_details(conn: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """Prints the schema and sample data for a given table.

    Args:
        conn: The DuckDB connection object.
        table_name: The name of the table to print details for.
    """
    print(f"- {table_name}")

    print("\nSchema:")
    table_schema = get_table_schema(conn, table_name)
    for col, dtype, nullable in table_schema:
        print(f"  {col}: {dtype} {'(nullable)' if nullable == 'YES' else ''}")

    print("\nSample data:")
    sample = get_sample_data(conn, table_name)

    if sample:
        columns = conn.execute(f"SELECT * FROM {table_name} LIMIT 0").description
        for col, val in zip([desc[0] for desc in columns], sample[0]):
            print(f"  {col}: {val}")
    print("\n" + "-" * 50)


def check_port_database_schema(db_path: Path) -> None:
    """Checks and prints the schema of the Port database.

    Args:
        db_path: The path to the Port database file.
    """
    if not db_path.exists():
        print(f"Port database not found at: {db_path}")
        return

    print("Checking Port database schema...")
    port_conn = get_port_db_connection(db_path)

    try:
        print("\nTables in Port database:")
        table_names = get_table_names(port_conn)
        for table in table_names:
            print_table_details(port_conn, table)
    except Exception as e:
        print(f"Error checking schemas: {str(e)}")
        raise e
    finally:
        port_conn.close()


def check_research_database_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Checks and prints the schema of the research database.

    Args:
        conn: The DuckDB connection object for the research database.
    """
    print("\nResearch Database Schema:")
    research_schema = conn.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'companies'
        ORDER BY ordinal_position
    """
    ).fetchall()

    for col, dtype, nullable in research_schema:
        print(f"{col}: {dtype} {'(nullable)' if nullable == 'YES' else ''}")


def check_schemas() -> None:
    """Check and compare schemas of both databases"""
    PORT_DB = Path("/Users/srvo/notebooks/data/port.duckdb")

    check_port_database_schema(PORT_DB)

    from db import get_connection  # delayed import to avoid circular dependencies

    with get_connection() as conn:
        check_research_database_schema(conn)


if __name__ == "__main__":
    check_schemas()
```
