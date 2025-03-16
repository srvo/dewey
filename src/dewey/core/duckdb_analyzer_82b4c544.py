import importlib.util
import os
import subprocess
import sys
import venv
from typing import Any

# Path to the DuckDB files
DUCKDB_PATH = "/Users/srvo/Data/output_data/duckdb_files"


def create_virtual_environment() -> str:
    """Creates a virtual environment if it doesn't exist.

    Returns
    -------
        str: The path to the virtual environment directory.

    """
    venv_dir = "venv"
    if not os.path.exists(venv_dir):
        venv.create(venv_dir, with_pip=True)
    return venv_dir


def install_duckdb(venv_dir: str) -> None:
    """Installs the DuckDB Python package in the given virtual environment.

    Args:
    ----
        venv_dir: The path to the virtual environment directory.

    """
    os.path.join(venv_dir, "bin", "pip")
    python_path = os.path.join(venv_dir, "bin", "python")
    subprocess.check_call([python_path, "-m", "pip", "install", "duckdb"])


def load_duckdb(venv_dir: str) -> Any:
    """Loads the DuckDB module from the given virtual environment.

    Args:
    ----
        venv_dir: The path to the virtual environment directory.

    Returns:
    -------
        Any: The DuckDB module.

    Raises:
    ------
        ImportError: If DuckDB cannot be imported even after installation.

    """
    # Activate the virtual environment
    activate_path = os.path.join(venv_dir, "bin", "activate")
    with open(activate_path) as f:
        exec(f.read(), {"__file__": activate_path})

    # Now try to import duckdb within the activated environment
    if importlib.util.find_spec("duckdb") is None:
        install_duckdb(venv_dir)
        # After installation, try importing again
        if importlib.util.find_spec("duckdb") is None:
            msg = "Failed to import duckdb even after installation"
            raise ImportError(msg)
    return __import__("duckdb")


def process_database(db_path: str, duckdb: Any) -> dict[str, Any]:
    """Processes a single DuckDB database.

    Args:
    ----
        db_path: The path to the DuckDB database file.
        duckdb: The DuckDB module.

    Returns:
    -------
        A dictionary containing the database connection, schema, and table contents.

    """
    filename = os.path.basename(db_path)
    db_name = filename[:-3]  # Remove .db extension
    try:
        con = duckdb.connect(database=db_path)

        # Get schema information
        schema: list[tuple[str]] = con.execute("SHOW TABLES").fetchall()
        if not schema:
            con.close()
            os.remove(db_path)
            return {}

        # Store schema and content information
        database_info: dict[str, Any] = {
            "connection": con,
            "schema": schema,
            "tables": {},
        }

        # Get content from each table
        for table in schema:
            table_name: str = table[0]
            result = con.execute(f"SELECT * FROM {table_name}")
            rows: list[tuple[Any]] = result.fetchall()
            database_info["tables"][table_name] = rows

        return {db_name: database_info}

    except Exception:
        return {}


def load_and_analyze_databases() -> dict[str, Any]:
    """Loads and analyzes all DuckDB databases in the specified directory.

    Returns
    -------
        A dictionary containing information about the databases, including their
        schemas and content.

    """
    venv_dir = create_virtual_environment()
    try:
        duckdb = load_duckdb(venv_dir)
    except Exception:
        return {}

    # Initialize a dictionary to track database schemas and content
    databases: dict[str, Any] = {}

    # Load all DuckDB databases
    for filename in os.listdir(DUCKDB_PATH):
        if filename.endswith(".db"):
            db_path = os.path.join(DUCKDB_PATH, filename)
            db_data = process_database(db_path, duckdb)
            databases.update(db_data)

    return databases


def check_for_overlap(databases: dict[str, Any]) -> None:
    """Checks for schema and content overlaps between databases.

    Args:
    ----
        databases: A dictionary containing information about the databases.

    """
    if not databases:
        return

    # Check for schema overlap
    schemas: dict[str, bool] = {}
    for db_name, db_info in databases.items():
        for table in db_info["schema"]:
            table_name: str = table[0]
            # Simple schema representation (can be expanded)
            schema_key = f"{db_name}.{table_name}"
            if schema_key in schemas:
                pass
            schemas[schema_key] = True

    # Check for content overlap
    content_hashes: dict[int, str] = {}
    for db_name, db_info in databases.items():
        for table_name, rows in db_info["tables"].items():
            for row in rows:
                row_hash = hash(row)
                if row_hash in content_hashes:
                    pass
                content_hashes[row_hash] = f"{db_name}.{table_name}"


if __name__ == "__main__":
    try:
        databases = load_and_analyze_databases()
        check_for_overlap(databases)
    except Exception:
        sys.exit(1)
