"""Client Data Import Module

This module handles the import of client data from CSV files into a SQLite database.
It processes two main data sources:
1. Households data containing client-level information
2. Accounts data containing individual account details

The module creates two tables in the database:
- clients: Stores household-level client information
- client_accounts: Stores individual account details linked to households

Key Features:
- Data validation and cleaning
- Error logging and reporting
- Database schema management
- Bulk data import with transaction handling
"""

import logging
import sqlite3

import pandas as pd

# Configure logging for the import process
logging.basicConfig(
    filename="project.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("client_import")


def import_client_data(db_path: str, households_path: str, accounts_path: str) -> None:
    """Import client data from CSV files into SQLite database.

    Args:
    ----
        db_path (str): Path to SQLite database file
        households_path (str): Path to households CSV file
        accounts_path (str): Path to accounts CSV file

    Raises:
    ------
        Exception: If any error occurs during the import process
        sqlite3.Error: If database operations fail

    Returns:
    -------
        None

    """
    try:
        # Read CSV files into pandas DataFrames
        # Using pandas for efficient CSV parsing and data manipulation
        households_df = pd.read_csv(households_path)
        accounts_df = pd.read_csv(accounts_path)

        # Establish database connection
        # Using sqlite3 for lightweight database operations
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create clients table with appropriate schema
        # Using IF NOT EXISTS to prevent errors on subsequent runs
        # Schema includes:
        # - name: Primary key for client identification
        # - balance: Total household balance
        # - account_count: Number of accounts
        # - account_groups: Categorization of accounts
        # - cash_percentage: Percentage of cash holdings
        # - priority: Default priority level for client
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS clients (
            name TEXT PRIMARY KEY,
            balance REAL,
            account_count INTEGER,
            account_groups TEXT,
            cash_percentage REAL,
            priority INTEGER DEFAULT 5
        )
        """
        )

        # Process each household record
        # Using iterrows() for row-wise processing
        # Includes data validation and cleaning
        for _, row in households_df.iterrows():
            name = row["Name"]
            if pd.isna(name) or name == "":
                continue

            # Clean and convert balance string to float
            # Handles currency symbols and thousand separators
            balance = (
                float(row["Balance"].replace("$", "").replace(",", ""))
                if pd.notna(row["Balance"])
                else 0
            )

            # Insert or update client record
            # Using INSERT OR REPLACE to handle updates
            # All fields are parameterized for security
            cursor.execute(
                """
            INSERT OR REPLACE INTO clients
            (name, balance, account_count, account_groups, cash_percentage, priority)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    balance,
                    int(row["# of Accounts"]) if pd.notna(row["# of Accounts"]) else 0,
                    row["Account Groups"] if pd.notna(row["Account Groups"]) else "",
                    float(row["Cash"].rstrip("%")) if pd.notna(row["Cash"]) else 0,
                    5,  # All clients get priority 5
                ),
            )

            logger.info(f"Imported client: {name} with balance ${balance:,.2f}")

        conn.commit()

        # Log import summary statistics
        # Provides visibility into import results
        cursor.execute("SELECT COUNT(*), SUM(balance) FROM clients")
        count, total_balance = cursor.fetchone()
        logger.info(
            f"Imported {count} clients with total balance ${total_balance:,.2f}"
        )

        # Create client_accounts table with appropriate schema
        # Includes foreign key relationship to clients table
        # Schema includes:
        # - account_name: Primary key for account identification
        # - household: Foreign key to clients table
        # - portfolio: Investment portfolio type
        # - balance: Account balance
        # - custodian: Account custodian information
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS client_accounts (
            account_name TEXT PRIMARY KEY,
            household TEXT,
            portfolio TEXT,
            balance REAL,
            custodian TEXT,
            FOREIGN KEY (household) REFERENCES clients(name)
        )
        """
        )

        # Process and import individual accounts
        # Links accounts to their respective households
        for _, row in accounts_df.iterrows():
            if pd.isna(row["Name"]) or pd.isna(row["Household"]):
                continue

            balance = (
                float(row["Balance"].replace("$", "").replace(",", ""))
                if pd.notna(row["Balance"])
                else 0
            )

            cursor.execute(
                """
            INSERT OR REPLACE INTO client_accounts
            (account_name, household, portfolio, balance, custodian)
            VALUES (?, ?, ?, ?, ?)
            """,
                (
                    row["Name"],
                    row["Household"],
                    row["Portfolio"] if pd.notna(row["Portfolio"]) else "",
                    balance,
                    row["Custodian"] if pd.notna(row["Custodian"]) else "",
                ),
            )

        conn.commit()

        # Log accounts import summary
        # Provides visibility into account-level import results
        cursor.execute("SELECT COUNT(*), SUM(balance) FROM client_accounts")
        count, total_balance = cursor.fetchone()
        logger.info(
            f"Imported {count} accounts with total balance ${total_balance:,.2f}"
        )

    except Exception as e:
        logger.error(f"Error importing client data: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Default file paths for local development
    db_path = "email_data.db"
    households_path = "Households - 20250113.csv"
    accounts_path = "Open Accounts - 20250113.csv"

    # Execute the import process
    import_client_data(db_path, households_path, accounts_path)
