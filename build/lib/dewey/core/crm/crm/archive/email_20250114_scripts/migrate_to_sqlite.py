"""Script to migrate existing email data to SQLite database.
Dependencies:
- SQLite database
- pandas for data manipulation
- Logging utilities from log_analyzer.py
"""

import logging
import os

import pandas as pd

from scripts.db_connector import get_db

# Initialize logging to capture INFO and ERROR level logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def migrate_csv_to_sqlite(csv_path: str, table_name: str):
    """Migrates data from a CSV file to a specified SQLite table.

    Args:
    ----
        csv_path (str): Path to the source CSV file.
        table_name (str): Name of the target SQLite table.

    """
    try:
        # Read CSV data into pandas DataFrame
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from {csv_path}")

        # Insert data into SQLite database
        db = get_db()
        with db.get_connection() as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            logger.info(f"Migrated data to table '{table_name}' successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")


def main():
    """Main function to orchestrate the migration process."""
    csv_files = {
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
