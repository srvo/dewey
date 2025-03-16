```python
"""Script to migrate existing email data to SQLite database."""

import logging
import os
from typing import Dict

import pandas as pd

from scripts.db_connector import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def load_csv_to_dataframe(csv_path: str) -> pd.DataFrame:
    """Loads a CSV file into a pandas DataFrame.

    Args:
        csv_path: The path to the CSV file.

    Returns:
        A pandas DataFrame containing the data from the CSV file.
    """
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from {csv_path}")
        return df
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except pd.errors.EmptyDataError as e:
        logger.error(f"CSV file is empty: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        raise


def write_dataframe_to_sqlite(df: pd.DataFrame, table_name: str) -> None:
    """Writes a pandas DataFrame to an SQLite table.

    Args:
        df: The pandas DataFrame to write.
        table_name: The name of the SQLite table.
    """
    try:
        db = get_db()
        with db.get_connection() as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            logger.info(f"Migrated data to table '{table_name}' successfully.")
    except Exception as e:
        logger.error(f"Error writing to SQLite: {e}")
        raise


def migrate_csv_to_sqlite(csv_path: str, table_name: str) -> None:
    """Migrates data from a CSV file to a specified SQLite table.

    Args:
        csv_path: The path to the source CSV file.
        table_name: The name of the target SQLite table.
    """
    try:
        df = load_csv_to_dataframe(csv_path)
        write_dataframe_to_sqlite(df, table_name)
    except Exception as e:
        logger.error(f"Migration failed for {csv_path} to {table_name}: {e}")


def main() -> None:
    """Main function to orchestrate the migration process."""
    csv_files: Dict[str, str] = {
        "raw_emails": "data/raw_emails.csv",
        "processed_contacts": "data/processed_contacts.csv",
    }

    for table, path in csv_files.items():
        if os.path.exists(path):
            migrate_csv_to_sqlite(path, table)
        else:
            logger.warning(
                f"CSV file '{path}' does not exist. Skipping migration for table '{table}'."
            )

    logger.info("Data migration process completed.")


if __name__ == "__main__":
    logger.info("Starting data migration to SQLite.")
    main()
    logger.info("Data migration to SQLite completed successfully.")
```
