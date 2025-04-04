#!/usr/bin/env python3
"""
Utility script to check data integrity and status across various parts of the system.

Usage:
python scripts/check_data.py [COMMAND] [OPTIONS]

Commands:
db      Check PostgreSQL database structure and content.
gmail   Check Gmail API connection and email data.
contacts Check unified contacts data.
"""

import typer
from dewey.core.base_script import BaseScript
from dewey.core.exceptions import DatabaseConnectionError
from sqlalchemy import text

# Assuming gmail utils are structured as in the original check_gmail.py
# Adjust imports based on actual location if different
try:
    # check_email_content, # Not including content check for brevity
    # check_enrichment_status # Not including enrichment check
    from src.dewey.core.crm.gmail.gmail_api_test import test_gmail_api
    from src.dewey.core.crm.gmail.gmail_utils import (
        check_email_count,  # Assuming this queries the DB now
        check_email_schema,  # Assuming this queries the DB now
    )

    GMAIL_UTILS_AVAILABLE = True
except ImportError:
    GMAIL_UTILS_AVAILABLE = False


app = typer.Typer()


class CheckDataScript(BaseScript):
    """Base class for check commands, ensuring DB connection if needed."""

    def __init__(self, requires_db=False, config_section="checks"):
        # Determine project root dynamically if possible, or adjust as needed
        # This is a basic way, might need refinement based on project setup
        from pathlib import Path

        project_root = Path(
            __file__,
        ).parent.parent  # Assuming scripts/ is one level down from root

        super().__init__(
            project_root=str(project_root),  # Pass project_root to BaseScript
            config_section=config_section,
            requires_db=requires_db,
            # Add other BaseScript args as needed (e.g., enable_llm=False)
        )

    def execute(self) -> None:
        """
        Execute the data check script.

        This method is intentionally left blank as the data checks are
        performed by the subcommands. This ensures that the BaseScript
        is initialized correctly for all subcommands.
        """
        self.logger.info(
            "CheckDataScript execute method called (doing nothing). Use subcommands.",
        )


# --- Database Check Subcommand ---
db_app = typer.Typer()


@db_app.command("structure")
def check_db_structure(limit: int = typer.Option(1, help="Limit for sample data.")):
    """Check PostgreSQL database structure, row counts, and sample data."""
    script = CheckDataScript(requires_db=True, config_section="db_check")
    script.logger.info("Checking database structure...")

    try:
        with script.db_connection() as conn:  # Use BaseScript connection
            script.logger.info("Connected to database successfully")

            # Check if database has any tables
            tables_result = conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                """,
                ),
            ).fetchall()

            tables = [row[0] for row in tables_result]

            if not tables:
                script.logger.warning("No tables found in the database")
                return

            script.logger.info(f"Found {len(tables)} tables:")
            for i, table_name in enumerate(tables):
                script.logger.info(f"{i + 1}. {table_name}")

                try:
                    # Get row count
                    count_query = text(
                        f'SELECT COUNT(*) FROM "{table_name}"',
                    )  # Use quotes for safety
                    count = conn.execute(count_query).scalar()
                    script.logger.info(f"   - {count} rows")

                    # Get column info
                    columns_query = text(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = :table
                        ORDER BY ordinal_position
                    """,
                    )
                    columns = conn.execute(
                        columns_query, {"table": table_name},
                    ).fetchall()
                    script.logger.info(f"   - Columns ({len(columns)}):")
                    for col_name, col_type in columns:
                        script.logger.info(f"      - {col_name} ({col_type})")

                    # If table has rows, show a sample
                    if count > 0 and limit > 0:
                        # Note: Using f-string for table name is generally safe here as it comes
                        # from information_schema, but use with caution. Parameterization is preferred.
                        sample_query = text(
                            f'SELECT * FROM "{table_name}" LIMIT :limit',
                        )
                        sample = conn.execute(sample_query, {"limit": limit}).fetchone()
                        script.logger.info(
                            f"   - Sample data (limit {limit}): {sample}",
                        )

                except Exception as e:
                    script.logger.error(
                        f"   - Error inspecting table {table_name}: {e}",
                    )

        script.logger.info("Database check completed successfully")

    except DatabaseConnectionError as e:
        script.logger.error(f"Database connection error: {e}")
    except Exception as e:
        script.logger.error(f"Error examining database: {e}")


# --- Gmail Check Subcommand ---
gmail_app = typer.Typer()


@gmail_app.command("api")
def check_gmail_api():
    """Test connection to the Gmail API."""
    script = CheckDataScript(requires_db=False, config_section="gmail_check")
    if not GMAIL_UTILS_AVAILABLE:
        script.logger.error("Gmail utilities not found. Cannot perform check.")
        return

    script.logger.info("Testing Gmail API connection...")
    try:
        success = test_gmail_api()  # Assuming test_gmail_api takes no args
        script.logger.info(f"Gmail API test: {'PASSED' if success else 'FAILED'}")
    except Exception as e:
        script.logger.error(f"Error testing Gmail API: {e}")


@gmail_app.command("count")
def check_gmail_count():
    """Check the count of emails in the 'emails' database table."""
    script = CheckDataScript(requires_db=True, config_section="gmail_check")
    script.logger.info("Checking email count in database...")
    try:
        with script.db_connection() as conn:
            # Assuming table is named 'emails'
            count = conn.execute(text("SELECT COUNT(*) FROM emails")).scalar()
            script.logger.info(f"Total emails in 'emails' table: {count}")
    except DatabaseConnectionError as e:
        script.logger.error(f"Database connection error: {e}")
    except Exception as e:
        script.logger.error(f"Error counting emails in DB: {e}")


@gmail_app.command("schema")
def check_gmail_schema():
    """Check the schema of the 'emails' table in the database."""
    script = CheckDataScript(requires_db=True, config_section="gmail_check")
    script.logger.info("Checking 'emails' table schema...")
    try:
        with script.db_connection() as conn:
            columns_query = text(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'emails'
                ORDER BY ordinal_position
            """,
            )
            columns = conn.execute(columns_query).fetchall()
            if columns:
                script.logger.info("Email schema:")
                for col_name, col_type in columns:
                    script.logger.info(f"  {col_name} ({col_type})")
            else:
                script.logger.warning(
                    "Could not find 'emails' table or it has no columns.",
                )
    except DatabaseConnectionError as e:
        script.logger.error(f"Database connection error: {e}")
    except Exception as e:
        script.logger.error(f"Error checking email schema: {e}")


# --- Contacts Check Subcommand ---
contacts_app = typer.Typer()


@contacts_app.command("unified")
def check_unified_contacts(
    limit: int = typer.Option(3, help="Limit for sample data."),
    show_domains: bool = typer.Option(
        True, help="Show top domains by count (limit 10).",
    ),
):
    """Check unified_contacts table: count, schema, sample data, domains."""
    script = CheckDataScript(requires_db=True, config_section="contacts_check")
    script.logger.info("Checking unified contacts...")

    try:
        with script.db_connection() as conn:
            # Get total count
            count = conn.execute(text("SELECT COUNT(*) FROM unified_contacts")).scalar()
            script.logger.info(f"Total contacts in unified_contacts: {count}")

            # Get table schema
            schema_query = text(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'unified_contacts'
                ORDER BY ordinal_position
            """,
            )
            schema_result = conn.execute(schema_query).fetchall()
            script.logger.info("Table schema:")
            for col_name, col_type in schema_result:
                script.logger.info(f"- {col_name}: {col_type}")

            # Get sample data
            if count > 0 and limit > 0:
                sample_query = text("SELECT * FROM unified_contacts LIMIT :limit")
                sample_result = conn.execute(sample_query, {"limit": limit}).fetchall()
                script.logger.info(f"Sample contacts (limit {limit}):")
                for row in sample_result:
                    script.logger.info(f"- {row}")

            # Get domain statistics
            if show_domains:
                try:
                    # Use SUBSTRING for PostgreSQL compatibility
                    domain_query = text(
                        """
                        WITH email_domains AS (
                            SELECT
                                substring(email from '@(.*)$') AS domain
                            FROM unified_contacts
                            WHERE email IS NOT NULL AND email LIKE '%@%'
                        )
                        SELECT
                            domain,
                            COUNT(*) AS contact_count
                        FROM email_domains
                        WHERE domain IS NOT NULL AND domain <> ''
                        GROUP BY domain
                        ORDER BY contact_count DESC
                        LIMIT 10
                    """,
                    )
                    domain_result = conn.execute(domain_query).fetchall()

                    if domain_result:
                        script.logger.info("Top domains by contact count:")
                        for domain, contact_count in domain_result:
                            script.logger.info(f"- {domain}: {contact_count} contacts")
                    else:
                        script.logger.info("No valid email domains found to aggregate.")
                except Exception as e:
                    script.logger.error(f"Failed to retrieve email domains: {e}")

    except DatabaseConnectionError as e:
        script.logger.error(f"Database connection error: {e}")
    except Exception as e:
        script.logger.error(f"Error querying unified contacts: {e}")


# --- Main Application ---
app.add_typer(db_app, name="db", help="Database checks")
app.add_typer(gmail_app, name="gmail", help="Gmail integration checks")
app.add_typer(contacts_app, name="contacts", help="Contact data checks")

if __name__ == "__main__":
    app()
# Ensure BaseScript finds the project root correctly
# This might require adjusting the BaseScript init or how project_root is determined
# if CheckDataScript fails to load config/find .env
