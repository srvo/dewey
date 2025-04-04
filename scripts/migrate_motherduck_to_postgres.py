import datetime
import json  # Added json import needed for data conversion
import logging
import os
import sys
from decimal import Decimal

import duckdb

# Add project root to sys.path to allow importing dewey modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Restore Original Imports ---
try:
    # We need psycopg2 extras for execute_values and potentially specific types
    import psycopg2
    import psycopg2.extras
    from dewey.core.db.config import get_db_config
    from dewey.utils.database import (
        close_pool,
        execute_query,  # Direct execute_query for DDL might be needed
        get_db_cursor,
        initialize_pool,
        table_exists,
    )
except ImportError as e:
    print(f"Error importing Dewey modules: {e}")
    print(
        "Ensure the script is run from the project root or the environment is set up correctly.",
    )
    sys.exit(1)

# --- Restore Original Script Logic ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("motherduck_migrate")

# --- Type Mapping ---
# Basic DuckDB to PostgreSQL type mapping
DUCKDB_TO_POSTGRES_TYPES = {
    "VARCHAR": "TEXT",
    "STRING": "TEXT",
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "HUGEINT": "NUMERIC",  # No direct equivalent, use NUMERIC
    "SMALLINT": "SMALLINT",
    "TINYINT": "SMALLINT",  # No TINYINT in PG
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP WITH TIME ZONE",  # Assume TZ aware
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP_S": "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP_MS": "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP_NS": "TIMESTAMP WITH TIME ZONE",
    "TIME": "TIME",
    "DOUBLE": "DOUBLE PRECISION",
    "FLOAT": "REAL",
    "REAL": "REAL",
    "DECIMAL": "NUMERIC",  # Precision/scale might need adjustment
    "BLOB": "BYTEA",
    "UUID": "UUID",
    "JSON": "JSONB",
    # Arrays/Lists - map base type
    "INTEGER[]": "INTEGER[]",
    "VARCHAR[]": "TEXT[]",
    "STRING[]": "TEXT[]",
    "TEXT[]": "TEXT[]",
    "DOUBLE[]": "DOUBLE PRECISION[]",
    # Add other types as needed (INTERVAL, MAP, STRUCT require more complex handling)
}


def get_postgres_type(duckdb_type: str) -> str:
    """Maps DuckDB type string to PostgreSQL type string."""
    duckdb_type_upper = duckdb_type.upper()

    # Handle parameterized types like DECIMAL(18, 3) or VARCHAR(255)
    if "(" in duckdb_type_upper:
        base_type = duckdb_type_upper.split("(")[0]
        if base_type == "DECIMAL" or base_type == "NUMERIC":
            # Keep precision/scale for DECIMAL/NUMERIC
            return duckdb_type_upper
        if base_type == "VARCHAR":
            return "TEXT"  # Default to TEXT, or parse length if needed
        # For other parameterized types, try mapping the base type
        pg_type = DUCKDB_TO_POSTGRES_TYPES.get(base_type, "TEXT")  # Default to TEXT
        logger.warning(
            f"Using default mapping '{pg_type}' for parameterized DuckDB type: {duckdb_type}",
        )
        return pg_type

    # Handle arrays specifically
    if duckdb_type_upper.endswith("[]"):
        base_type = duckdb_type_upper[:-2]
        pg_base_type = DUCKDB_TO_POSTGRES_TYPES.get(
            base_type, "TEXT",
        )  # Default base to TEXT
        return f"{pg_base_type}[]"

    # Direct mapping or default
    return DUCKDB_TO_POSTGRES_TYPES.get(
        duckdb_type_upper, "TEXT",
    )  # Default unknown types to TEXT


def get_motherduck_connection() -> duckdb.DuckDBPyConnection:
    """Establishes connection to MotherDuck."""
    logger.info("Attempting to connect to MotherDuck...")
    md_token = os.environ.get("MOTHERDUCK_TOKEN")
    md_db = os.environ.get(
        "DEWEY_MOTHERDUCK_DB", "md:dewey",
    )  # Get MD db name from env or default

    if not md_token:
        logger.error("MOTHERDUCK_TOKEN environment variable not set.")
        raise ConnectionError("MotherDuck token not found.")

    try:
        # Ensure token is set for the connection context
        # DuckDB reads MOTHERDUCK_TOKEN env var automatically if set
        conn_string = md_db  # Use the database name directly
        logger.info(f"Connecting to MotherDuck database: {conn_string}")
        conn = duckdb.connect(conn_string, read_only=True)  # Connect read-only
        logger.info("Successfully connected to MotherDuck.")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MotherDuck: {e}", exc_info=True)
        raise


def migrate_table(
    md_conn: duckdb.DuckDBPyConnection, table_name: str, schema_name: str = "main",
):
    """Migrates a single table from MotherDuck to PostgreSQL."""
    logger.info(f"Starting migration for table: {schema_name}.{table_name}")

    try:
        # 1. Get Schema from MotherDuck
        logger.debug(f"Fetching schema for {table_name} from MotherDuck...")
        try:
            schema_query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = ? AND table_name = ?
            ORDER BY ordinal_position;
            """
            columns_info = md_conn.execute(
                schema_query, [schema_name, table_name],
            ).fetchall()
        except Exception as e:
            logger.error(
                f"Failed to fetch schema for {table_name} from MotherDuck: {e}",
            )
            return  # Skip table if schema fetch fails

        if not columns_info:
            logger.warning(f"No columns found for table {table_name}. Skipping.")
            return

        column_names = [col[0] for col in columns_info]
        pg_column_defs = []
        for col_name, duckdb_type in columns_info:
            pg_type = get_postgres_type(duckdb_type)
            pg_column_defs.append(f'"{col_name}" {pg_type}')  # Quote column names

        logger.info(f"Fetched schema for {table_name}: {len(column_names)} columns.")
        logger.debug(f"PostgreSQL column definitions: {pg_column_defs}")

        # 2. Create Table in PostgreSQL
        pg_table_name = table_name  # Use the same table name for now
        if not table_exists(pg_table_name):
            logger.info(
                f"Table '{pg_table_name}' does not exist in PostgreSQL. Creating...",
            )
            create_table_sql = (
                f'CREATE TABLE "{pg_table_name}" ({", ".join(pg_column_defs)});'
            )
            try:
                # Use execute_query from utils for DDL
                execute_query(create_table_sql)
                logger.info(
                    f"Successfully created table '{pg_table_name}' in PostgreSQL.",
                )
            except Exception as e:
                logger.error(
                    f"Failed to create table '{pg_table_name}' in PostgreSQL: {e}",
                    exc_info=True,
                )
                logger.warning(
                    f"Skipping data migration for table {table_name} due to creation error.",
                )
                return  # Stop processing this table if creation fails
        else:
            logger.info(
                f"Table '{pg_table_name}' already exists in PostgreSQL. Skipping creation.",
            )
            # Optional: Add logic here to check if schemas match or clear existing data

        # 3. Fetch and Insert Data in Chunks
        logger.info(f"Fetching data from MotherDuck table {table_name}...")
        total_rows_inserted = 0
        chunk_size = 1000  # Process N rows at a time

        try:
            # Construct SELECT query quoting column names from schema
            select_columns = ", ".join([f'"{name}"' for name in column_names])
            md_select_query = (
                f'SELECT {select_columns} FROM "{schema_name}". "{table_name}";'
            )

            # Use fetch_record_batch for potentially better memory efficiency with Arrow
            stream = md_conn.execute(md_select_query).fetch_record_batch(chunk_size)

            pg_insert_cols = ", ".join([f'"{name}"' for name in column_names])
            pg_placeholders = ", ".join(["%s"] * len(column_names))
            pg_insert_sql = (
                f'INSERT INTO "{pg_table_name}" ({pg_insert_cols}) VALUES %s;'
            )

            chunk_num = 0
            while True:
                try:
                    # Fix the PyArrow API call
                    # Change from fetch_next_batch() to read_next_batch()
                    chunk = stream.read_next_batch()

                    if chunk is None:  # PyArrow returns None at the end
                        break  # No more data

                    chunk_num += 1
                    logger.info(
                        f"Processing chunk {chunk_num} with {len(chunk)} rows for {table_name}...",
                    )

                    # Convert Arrow chunk to list of tuples suitable for execute_values
                    # Handle type conversions that psycopg2 might not do automatically from Arrow
                    data_tuples = []
                    for i in range(len(chunk)):
                        row_list = []
                        for j, col_name in enumerate(column_names):
                            value = chunk.column(j)[i].as_py()
                            # Specific type handling if needed (e.g., Decimal, datetime)
                            if isinstance(value, Decimal):
                                # psycopg2 can handle Decimal directly
                                row_list.append(value)
                            elif isinstance(
                                value, (datetime.datetime, datetime.date, datetime.time),
                            ):
                                # psycopg2 handles these directly
                                row_list.append(value)
                            elif isinstance(value, list):
                                # psycopg2 handles lists for array types
                                row_list.append(value)
                            elif isinstance(value, dict):
                                # Convert dict to JSON string for JSON/JSONB
                                row_list.append(json.dumps(value))
                            elif value is None:
                                row_list.append(None)
                            else:
                                # Default to string conversion? Or rely on psycopg2 type adaptation
                                row_list.append(value)
                        data_tuples.append(tuple(row_list))

                    # Insert chunk into PostgreSQL using execute_values
                    with get_db_cursor(commit=True) as pg_cursor:
                        psycopg2.extras.execute_values(
                            pg_cursor,
                            pg_insert_sql,
                            data_tuples,
                            page_size=chunk_size,  # Match chunk size
                        )
                    total_rows_inserted += len(data_tuples)
                    logger.info(
                        f"Inserted {len(data_tuples)} rows into {pg_table_name}. Total inserted: {total_rows_inserted}",
                    )

                except StopIteration:
                    logger.info(f"Finished fetching data for {table_name}.")
                    break  # End of data stream
                except Exception as e:
                    logger.error(
                        f"Error processing chunk {chunk_num} for table {table_name}: {e}",
                        exc_info=True,
                    )
                    # Optionally break or continue to next chunk? For now, stop migration for this table on chunk error.
                    logger.warning(
                        f"Stopping migration for {table_name} due to error in chunk {chunk_num}.",
                    )
                    return

        except Exception as e:
            logger.error(
                f"Error fetching/inserting data for table {table_name}: {e}",
                exc_info=True,
            )
            return  # Stop migration for this table on general fetch/insert error

        logger.info(
            f"Successfully migrated {total_rows_inserted} rows for table {table_name}.",
        )

    except Exception as e:
        logger.error(
            f"Unhandled error during migration for table {table_name}: {e}",
            exc_info=True,
        )


def main():
    """Main migration function."""
    md_conn = None
    try:
        # 1. Initialize PG Pool
        logger.info("Initializing PostgreSQL connection pool...")
        initialize_pool()
        logger.info("PostgreSQL pool initialized.")

        # 2. Connect to MotherDuck
        md_conn = get_motherduck_connection()

        # 3. List Tables in MotherDuck (user tables in 'main' schema usually)
        logger.info("Fetching list of tables from MotherDuck...")
        try:
            tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_type = 'BASE TABLE';
            """
            tables = md_conn.execute(tables_query).fetchall()
            table_names = [t[0] for t in tables]
            logger.info(f"Found {len(table_names)} tables in MotherDuck: {table_names}")
        except Exception as e:
            logger.error(f"Failed to list tables from MotherDuck: {e}")
            return

        # 4. Migrate Each Table
        for table_name in table_names:
            # Basic check to skip duckdb system tables if somehow listed
            if table_name.startswith("duckdb_") or table_name.startswith("sqlite_"):
                logger.debug(f"Skipping system table: {table_name}")
                continue
            migrate_table(md_conn, table_name, schema_name="main")

        logger.info("Migration process finished.")

    except ConnectionError as e:
        logger.critical(f"Database connection failed: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        # 5. Close Connections
        if md_conn:
            try:
                md_conn.close()
                logger.info("MotherDuck connection closed.")
            except Exception as e:
                logger.error(f"Error closing MotherDuck connection: {e}")
        try:
            close_pool()
            logger.info("PostgreSQL connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing PostgreSQL pool: {e}")


if __name__ == "__main__":
    main()
