```python
import importlib.util
import os
import subprocess
import sys
import venv
from typing import Dict, List, Tuple, Any

# Path to the DuckDB files
DUCKDB_PATH = "/Users/srvo/Data/output_data/duckdb_files"


def create_virtual_environment() -> str:
    """Creates a virtual environment if one doesn't exist.

    Returns:
        str: The path to the created virtual environment.
    """
    venv_dir = "venv"
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
        print("Virtual environment created successfully!")
    return venv_dir


def install_duckdb(venv_dir: str) -> None:
    """Installs the DuckDB Python package in the given virtual environment.

    Args:
        venv_dir: The path to the virtual environment.
    """
    print("Installing DuckDB Python package...")
    pip_path = os.path.join(venv_dir, "bin", "pip")
    python_path = os.path.join(venv_dir, "bin", "python")
    subprocess.check_call([python_path, "-m", "pip", "install", "duckdb"])
    print("DuckDB installed successfully!")


def load_duckdb(venv_dir: str) -> Any:
    """Loads the DuckDB module within the specified virtual environment.

    Args:
        venv_dir: The path to the virtual environment.

    Returns:
        Any: The DuckDB module.

    Raises:
        ImportError: If DuckDB fails to import even after installation.
    """
    # Activate the virtual environment
    activate_path = os.path.join(venv_dir, "bin", "activate")
    with open(activate_path) as f:
        exec(f.read(), {"__file__": activate_path})

    # Now try to import duckdb within the activated environment
    if importlib.util.find_spec('duckdb') is None:
        print("DuckDB Python package not found. Installing it...")
        install_duckdb(venv_dir)
        # After installation, try importing again
        if importlib.util.find_spec('duckdb') is None:
            raise ImportError("Failed to import duckdb even after installation")
    return __import__('duckdb')


def load_and_analyze_databases() -> Dict[str, Dict[str, Any]]:
    """Loads and analyzes DuckDB databases in the specified path.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary containing database schemas and content.
    """
    venv_dir = create_virtual_environment()
    try:
        duckdb = load_duckdb(venv_dir)
    except Exception as e:
        print(f"Failed to load DuckDB: {str(e)}")
        return {}

    print(f"Processing databases in: {DUCKDB_PATH}")
    # Initialize a dictionary to track database schemas and content
    databases: Dict[str, Dict[str, Any]] = {}

    # Load all DuckDB databases
    for filename in os.listdir(DUCKDB_PATH):
        if filename.endswith(".db"):
            db_path = os.path.join(DUCKDB_PATH, filename)
            # Use a unique name for each database
            db_name = filename[:-3]  # Remove .db extension
            try:
                print(f"Processing database: {filename}")
                con = duckdb.connect(database=db_path)

                # Get schema information
                schema: List[Tuple[str]] = con.execute("SHOW TABLES").fetchall()
                print(f"Found {len(schema)} tables in {filename}")
                if not schema:
                    print(f"Database {filename} is empty - deleting")
                    con.close()
                    os.remove(db_path)
                    continue

                # Store schema and content information
                databases[db_name] = {
                    'connection': con,
                    'schema': schema,
                    'tables': {}
                }

                # Get content from each table
                for table in schema:
                    table_name = table[0]
                    print(f"Processing table: {table_name}")
                    result = con.execute(f"SELECT * FROM {table_name}")
                    rows: List[Tuple[Any]] = result.fetchall()
                    print(f"Found {len(rows)} rows in {table_name}")
                    databases[db_name]['tables'][table_name] = rows
            except Exception as e:
                print(f"Error processing database {filename}: {str(e)}")
                continue

    print(f"Processed {len(databases)} databases with content")
    return databases


def check_for_overlap(databases: Dict[str, Dict[str, Any]]) -> None:
    """Checks for schema and content overlaps between databases.

    Args:
        databases: A dictionary containing database schemas and content.
    """
    if not databases:
        print("No databases with content found - nothing to check for overlaps")
        return

    print("Checking for schema overlaps...")
    # Check for schema overlap
    schemas: Dict[str, bool] = {}
    for db_name, db_info in databases.items():
        for table in db_info['schema']:
            table_name = table[0]
            # Simple schema representation (can be expanded)
            schema_key = f"{db_name}.{table_name}"
            if schema_key in schemas:
                print(f"Schema overlap detected: {table_name} exists in both {schema_key} and {db_name}")
            schemas[schema_key] = True

    print("Checking for content overlaps...")
    # Check for content overlap
    content_hashes: Dict[int, str] = {}
    for db_name, db_info in databases.items():
        for table_name, rows in db_info['tables'].items():
            for row in rows:
                row_hash = hash(row)
                if row_hash in content_hashes:
                    print(f"Content overlap detected: Row {row} exists in both {content_hashes[row_hash]} and {db_name}.{table_name}")
                content_hashes[row_hash] = f"{db_name}.{table_name}"


if __name__ == "__main__":
    try:
        print("Starting database analysis...")
        databases = load_and_analyze_databases()
        print("\nChecking for overlaps...")
        check_for_overlap(databases)
        print("\nAnalysis completed successfully!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)
```
