from __future__ import annotations

import os

import duckdb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def upload_contacts_to_motherduck() -> bool | None:
    try:
        # Connect to local database first
        local_con = duckdb.connect("contacts.db")

        # Connect to MotherDuck using token from environment variable
        motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
        if not motherduck_token:
            msg = "MOTHERDUCK_TOKEN environment variable not found"
            raise ValueError(msg)

        # Attach MotherDuck
        local_con.sql("ATTACH 'md:'")

        # Create a new database in MotherDuck from the current database
        local_con.sql(
            "CREATE DATABASE IF NOT EXISTS contacts_cloud FROM CURRENT_DATABASE()",
        )

        # Verify the upload
        md_con = duckdb.connect("md:contacts_cloud")

        # Check contact count
        md_con.sql(
            """
            SELECT
                COUNT(*) as total_contacts,
                COUNT(DISTINCT domain) as unique_domains,
                COUNT(DISTINCT email) as unique_emails
            FROM contacts
        """,
        ).fetchdf()

        # Show sample of uploaded data
        md_con.sql(
            """
            SELECT *
            FROM contacts
            LIMIT 5
        """,
        ).fetchdf()

        # Close connections
        local_con.close()
        md_con.close()

    except Exception:
        return False


if __name__ == "__main__":
    upload_contacts_to_motherduck()
