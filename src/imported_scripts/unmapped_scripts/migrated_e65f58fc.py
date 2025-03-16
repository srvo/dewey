from __future__ import annotations

import re

import duckdb
import pandas as pd

# Initialize DuckDB connection
con = duckdb.connect("contacts.db")


def sanitize_column_name(name):
    # Replace spaces and special characters with underscore
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    # Ensure name starts with a letter
    if clean_name[0].isdigit():
        clean_name = "col_" + clean_name
    return clean_name.lower()


def clean_and_dedupe_contacts(df):
    """Clean and deduplicate contact data."""
    # Convert email addresses to lowercase
    df["email"] = df["email"].str.lower().str.strip()

    # Remove rows with invalid or empty emails
    df = df[df["email"].notna() & df["email"].str.contains("@")]

    # Check for duplicates
    dupes = df[df.duplicated(subset=["email"], keep=False)]
    if not dupes.empty:

        # For each duplicate email, keep the record with the most recent contact date
        df["last_contact_date"] = pd.to_datetime(
            df["last_contact_date"],
            errors="coerce",
        )
        df = df.sort_values("last_contact_date", ascending=False).drop_duplicates(
            subset=["email"],
            keep="first",
        )

    return df


def import_csv_to_contacts(csv_path) -> bool | None:
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)

        # Sanitize column names
        df.columns = [sanitize_column_name(col) for col in df.columns]

        # Clean and dedupe the data
        df = clean_and_dedupe_contacts(df)

        # Get all columns from CSV except 'domain' if it exists
        csv_columns = [col for col in df.columns if col != "domain"]

        # Create or alter table to accommodate all columns
        columns_def = (
            ", ".join([f'"{col}" VARCHAR' for col in csv_columns])
            + ', "domain" VARCHAR'
        )

        # Drop existing table if it exists
        con.execute("DROP TABLE IF EXISTS contacts")

        # Create new table
        create_table_sql = f"""
            CREATE TABLE contacts (
                {columns_def},
                UNIQUE("email")
            )
        """
        con.execute(create_table_sql)

        # Extract domain from email addresses
        df["domain"] = df["email"].str.split("@").str[1]

        # Prepare column list for INSERT statement
        columns_list = ", ".join([f'"{col}"' for col in [*csv_columns, "domain"]])

        # Insert data into DuckDB
        insert_query = f"""
            INSERT INTO contacts ({columns_list})
            SELECT {columns_list} FROM df
        """
        con.execute(insert_query)

        return True

    except Exception:
        return False


# Specific path to your CSV file
csv_path = "/Users/srvo/Development/.ipynb_checkpoints/DB - Contacts-2.csv"

# Import the CSV file
import_csv_to_contacts(csv_path)

# Verify the updated database
result = con.execute(
    """
    SELECT
        COUNT(*) as total_contacts,
        COUNT(DISTINCT domain) as unique_domains,
        COUNT(DISTINCT email) as unique_emails
    FROM contacts
""",
).fetchdf()

# Show duplicate check
dupes = con.execute(
    """
    SELECT email, COUNT(*) as count
    FROM contacts
    GROUP BY email
    HAVING COUNT(*) > 1
""",
).fetchdf()

# Show schema
schema = con.execute("DESCRIBE contacts").fetchdf()

# Show sample of records with all columns
sample = con.execute(
    """
    SELECT *
    FROM contacts
    LIMIT 5
""",
).fetchdf()

# Show top domains
domain_stats = con.execute(
    """
    SELECT
        domain,
        COUNT(*) as contact_count,
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM contacts) as percentage
    FROM contacts
    GROUP BY domain
    ORDER BY contact_count DESC
    LIMIT 10
""",
).fetchdf()

# Close connection
con.close()
