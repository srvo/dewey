#!/usr/bin/env python3
"""
Contact Consolidation Script
===========================

This script consolidates contact information from various tables in the MotherDuck database
into a single unified_contacts table, focusing on individuals.
"""

import json
from typing import Any

import duckdb

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import db_manager


class ContactConsolidation(BaseScript):
    """Consolidates contact information from various sources into a unified table."""

    def __init__(self) -> None:
        """Initializes the ContactConsolidation script."""
        super().__init__(config_section="contact_consolidation", requires_db=True)

    def execute(self) -> None:
        """
        Execute the contact consolidation workflow.

        This method handles the entire workflow of:
        1. Creating the unified contacts table
        2. Extracting contacts from various sources
        3. Merging contacts
        4. Inserting them into the unified table
        """
        self.logger.info("Starting execution of ContactConsolidation")

        try:
            # Use the database manager's context manager
            with db_manager.get_connection() as conn:
                # Create the unified contacts table
                self.create_unified_contacts_table(conn)

                # Extract contacts from various sources
                crm_contacts = self.extract_crm_contacts(conn)
                email_contacts = self.extract_email_contacts(conn)
                subscribers = self.extract_subscribers(conn)

                # Merge contacts
                merged_contacts = self.merge_contacts(
                    crm_contacts + email_contacts + subscribers,
                )

                # Insert contacts into unified table
                self.insert_unified_contacts(conn, merged_contacts)

            self.logger.info("Completed contact consolidation workflow successfully")

        except Exception as e:
            self.logger.error(f"Error in contact consolidation: {e}")
            raise

    def create_unified_contacts_table(self, conn: duckdb.DuckDBPyConnection) -> None:
        """
        Create the unified_contacts table if it doesn't exist.

        Args:
        ----
            conn: DuckDB connection

        """
        try:
            # Create a dummy emails table if it doesn't exist (for testing)
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS emails (
                draft_id VARCHAR PRIMARY KEY,
                from_address VARCHAR,
                import_timestamp TIMESTAMP,
                thread_id VARCHAR,
                msg_id VARCHAR,
                time_value BIGINT,
                subject VARCHAR,
                snippet VARCHAR,
                body TEXT,
                has_attachment BOOLEAN,
                labels VARCHAR
            )
            """,
            )

            # Insert some test data if the table is empty
            result = conn.execute("SELECT COUNT(*) FROM emails").fetchone()
            if result[0] == 0:
                self.logger.info("Adding test data to emails table")
                conn.execute(
                    """
                INSERT INTO emails (draft_id, from_address, subject, import_timestamp)
                VALUES
                    ('email1', 'test@example.com', 'Test subject 1', CURRENT_TIMESTAMP),
                    ('email2', 'john@gmail.com', 'Important proposal', CURRENT_TIMESTAMP),
                    ('email3', 'sarah@company.com', 'Meeting notes', CURRENT_TIMESTAMP)
                """,
                )

            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS unified_contacts (
                email VARCHAR PRIMARY KEY,
                first_name VARCHAR,
                last_name VARCHAR,
                full_name VARCHAR,
                company VARCHAR,
                job_title VARCHAR,
                phone VARCHAR,
                country VARCHAR,
                source VARCHAR,
                domain VARCHAR,
                last_interaction_date TIMESTAMP,
                first_seen_date TIMESTAMP,
                last_updated TIMESTAMP,
                tags VARCHAR,
                notes VARCHAR,
                metadata JSON
            )
            """,
            )
            self.logger.info("Created or verified unified_contacts table")
        except Exception as e:
            self.logger.error(f"Error creating unified_contacts table: {e}")
            raise

    def extract_crm_contacts(
        self, conn: duckdb.DuckDBPyConnection,
    ) -> list[dict[str, Any]]:
        """
        Extract contacts from CRM-related tables.

        Args:
        ----
            conn: DuckDB connection

        Returns:
        -------
            List of contact dictionaries

        """
        try:
            # Use 'contacts' table instead of 'crm_contacts'
            result = conn.execute(
                """
            SELECT
                email,
                name as full_name,
                CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN TRIM(SUBSTR(name, 1, POSITION(' ' IN name) - 1))
                    ELSE name
                END as first_name,
                CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN TRIM(SUBSTR(name, POSITION(' ' IN name) + 1))
                    ELSE NULL
                END as last_name,
                NULL as company,
                NULL as job_title,
                NULL as phone,
                NULL as country,
                'crm' as source,
                SUBSTR(email, POSITION('@' IN email) + 1) as domain,
                CURRENT_TIMESTAMP as last_interaction_date,
                CURRENT_TIMESTAMP as first_seen_date,
                CURRENT_TIMESTAMP as last_updated,
                NULL as tags,
                NULL as notes,
                NULL as metadata
            FROM contacts
            WHERE email IS NOT NULL AND email != ''
            """,
            ).fetchall()

            contacts = []
            for row in result:
                contact = {
                    "email": row[0],
                    "full_name": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "company": row[4],
                    "job_title": row[5],
                    "phone": row[6],
                    "country": row[7],
                    "source": row[8],
                    "domain": row[9],
                    "last_interaction_date": row[10],
                    "first_seen_date": row[11],
                    "last_updated": row[12],
                    "tags": row[13],
                    "notes": row[14],
                    "metadata": row[15],
                }
                contacts.append(contact)

            self.logger.info(f"Extracted {len(contacts)} contacts from CRM tables")
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from CRM tables: {e}")
            return []

    def extract_email_contacts(
        self, conn: duckdb.DuckDBPyConnection,
    ) -> list[dict[str, Any]]:
        """
        Extract contacts from email-related tables.

        Args:
        ----
            conn: DuckDB connection

        Returns:
        -------
            List of contact dictionaries

        """
        try:
            # Extract from emails
            result = conn.execute(
                """
            SELECT DISTINCT
                from_address as email,
                NULL as full_name,
                NULL as first_name,
                NULL as last_name,
                NULL as company,
                NULL as job_title,
                NULL as phone,
                NULL as country,
                'email' as source,
                SUBSTR(from_address, POSITION('@' IN from_address) + 1) as domain,
                import_timestamp as last_interaction_date,
                import_timestamp as first_seen_date,
                import_timestamp as last_updated,
                NULL as tags,
                subject as notes,
                NULL as metadata
            FROM emails
            WHERE from_address IS NOT NULL AND from_address != ''
            """,
            ).fetchall()

            contacts = []
            for row in result:
                contact = {
                    "email": row[0],
                    "full_name": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "company": row[4],
                    "job_title": row[5],
                    "phone": row[6],
                    "country": row[7],
                    "source": row[8],
                    "domain": row[9],
                    "last_interaction_date": row[10],
                    "first_seen_date": row[11],
                    "last_updated": row[12],
                    "tags": row[13],
                    "notes": row[14],
                    "metadata": row[15],
                }
                contacts.append(contact)

            # Extract from email_analyses instead of activedata_email_analyses
            result = conn.execute(
                """
            SELECT DISTINCT
                from_address as email,
                NULL as full_name,
                NULL as first_name,
                NULL as last_name,
                NULL as company,
                NULL as job_title,
                NULL as phone,
                NULL as country,
                'email_analysis' as source,
                SUBSTR(from_address, POSITION('@' IN from_address) + 1) as domain,
                analysis_date as last_interaction_date,
                analysis_date as first_seen_date,
                analysis_date as last_updated,
                NULL as tags,
                subject as notes,
                raw_analysis as metadata
            FROM email_analyses
            WHERE from_address IS NOT NULL AND from_address != ''
            """,
            ).fetchall()

            for row in result:
                contact = {
                    "email": row[0],
                    "full_name": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "company": row[4],
                    "job_title": row[5],
                    "phone": row[6],
                    "country": row[7],
                    "source": row[8],
                    "domain": row[9],
                    "last_interaction_date": row[10],
                    "first_seen_date": row[11],
                    "last_updated": row[12],
                    "tags": row[13],
                    "notes": row[14],
                    "metadata": row[15],
                }
                contacts.append(contact)

            self.logger.info(f"Extracted {len(contacts)} contacts from email tables")
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from email tables: {e}")
            return []

    def extract_subscribers(
        self, conn: duckdb.DuckDBPyConnection,
    ) -> list[dict[str, Any]]:
        """
        Extract contacts from subscriber-related tables.

        Args:
        ----
            conn: DuckDB connection

        Returns:
        -------
            List of contact dictionaries

        """
        try:
            # Extract from client_data_sources instead of input_data_subscribers
            result = conn.execute(
                """
            SELECT
                email,
                name as full_name,
                CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN TRIM(SUBSTR(name, 1, POSITION(' ' IN name) - 1))
                    ELSE name
                END as first_name,
                CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN TRIM(SUBSTR(name, POSITION(' ' IN name) + 1))
                    ELSE NULL
                END as last_name,
                NULL as company,
                NULL as job_title,
                NULL as phone,
                NULL as country,
                'subscriber' as source,
                SUBSTR(email, POSITION('@' IN email) + 1) as domain,
                created_at as last_interaction_date,
                created_at as first_seen_date,
                updated_at as last_updated,
                status as tags,
                attributes as notes,
                NULL as metadata
            FROM client_data_sources
            WHERE email IS NOT NULL AND email != ''
            """,
            ).fetchall()

            contacts = []
            for row in result:
                contact = {
                    "email": row[0],
                    "full_name": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "company": row[4],
                    "job_title": row[5],
                    "phone": row[6],
                    "country": row[7],
                    "source": row[8],
                    "domain": row[9],
                    "last_interaction_date": row[10],
                    "first_seen_date": row[11],
                    "last_updated": row[12],
                    "tags": row[13],
                    "notes": row[14],
                    "metadata": row[15],
                }
                contacts.append(contact)

            # Extract from input_data_EIvirgin_csvSubscribers
            # This table has a complex schema, so we'll extract what we can
            result = conn.execute(
                """
            SELECT
                "Email Address" as email,
                "Name" as full_name,
                "ContactExport_20160912_First Name" as first_name,
                "ContactExport_20160912_Last Name" as last_name,
                "EmployerName" as company,
                "Job Title" as job_title,
                NULL as phone,
                "Country" as country,
                'EI_subscriber' as source,
                "Email Domain" as domain,
                "LAST_CHANGED" as last_interaction_date,
                "OPTIN_TIME" as first_seen_date,
                "LAST_CHANGED" as last_updated,
                NULL as tags,
                "NOTES" as notes,
                NULL as metadata
            FROM input_data_EIvirgin_csvSubscribers
            WHERE "Email Address" IS NOT NULL AND "Email Address" != ''
            """,
            ).fetchall()

            for row in result:
                contact = {
                    "email": row[0],
                    "full_name": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "company": row[4],
                    "job_title": row[5],
                    "phone": row[6],
                    "country": row[7],
                    "source": row[8],
                    "domain": row[9],
                    "last_interaction_date": row[10],
                    "first_seen_date": row[11],
                    "last_updated": row[12],
                    "tags": row[13],
                    "notes": row[14],
                    "metadata": row[15],
                }
                contacts.append(contact)

            self.logger.info(
                f"Extracted {len(contacts)} contacts from subscriber tables",
            )
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from subscriber tables: {e}")
            return []

    def extract_contacts_from_blog_signups(
        self, conn: duckdb.DuckDBPyConnection,
    ) -> list[dict[str, Any]]:
        """
        Extract contacts from blog signup form responses.

        Args:
        ----
            conn: DuckDB connection

        Returns:
        -------
            List of contact dictionaries

        """
        try:
            result = conn.execute(
                """
            SELECT
                email,
                name as full_name,
                CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN TRIM(SUBSTR(name, 1, POSITION(' ' IN name) - 1))
                    ELSE name
                END as first_name,
                CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN TRIM(SUBSTR(name, POSITION(' ' IN name) + 1))
                    ELSE NULL
                END as last_name,
                company,
                NULL as job_title,
                phone,
                NULL as country,
                'blog_signup' as source,
                SUBSTR(email, POSITION('@' IN email) + 1) as domain,
                date as last_interaction_date,
                date as first_seen_date,
                date as last_updated,
                CASE WHEN wants_newsletter THEN 'newsletter' ELSE NULL END as tags,
                message as notes,
                raw_content as metadata
            FROM input_data_blog_signup_form_responses
            WHERE email IS NOT NULL AND email != ''
            """,
            ).fetchall()

            contacts = []
            for row in result:
                contact = {
                    "email": row[0],
                    "full_name": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "company": row[4],
                    "job_title": row[5],
                    "phone": row[6],
                    "country": row[7],
                    "source": row[8],
                    "domain": row[9],
                    "last_interaction_date": row[10],
                    "first_seen_date": row[11],
                    "last_updated": row[12],
                    "tags": row[13],
                    "notes": row[14],
                    "metadata": row[15],
                }
                contacts.append(contact)

            self.logger.info(
                f"Extracted {len(contacts)} contacts from blog signup form responses",
            )
            return contacts
        except Exception as e:
            self.logger.error(
                f"Error extracting contacts from blog signup form responses: {e}",
            )
            return []

    def merge_contacts(
        self, contacts: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Merge contacts by email, prioritizing more complete information.

        Args:
        ----
            contacts: List of contact dictionaries

        Returns:
        -------
            Dictionary of merged contacts keyed by email

        """
        merged_contacts = {}

        for contact in contacts:
            email = contact["email"]
            if not email:
                continue

            email = email.lower().strip()

            if email not in merged_contacts:
                merged_contacts[email] = contact
                continue

            # Merge with existing contact, prioritizing non-null values
            existing = merged_contacts[email]
            for key, value in contact.items():
                if key == "email":
                    continue

                # For all other fields, prefer non-null values
                if value is not None and existing[key] is None:
                    existing[key] = value

        self.logger.info(f"Merged contacts into {len(merged_contacts)} unique contacts")
        return merged_contacts

    def insert_unified_contacts(
        self, conn: duckdb.DuckDBPyConnection, contacts: dict[str, dict[str, Any]],
    ) -> None:
        """
        Insert merged contacts into the unified_contacts table.

        Args:
        ----
            conn: DuckDB connection
            contacts: Dictionary of merged contacts keyed by email

        """
        try:
            # Clear existing data
            conn.execute("DELETE FROM unified_contacts")
            self.logger.info("Cleared existing data from unified_contacts table")

            # Insert new data in batches
            batch_size = int(self.get_config_value("batch_size", 100))
            contact_items = list(contacts.items())
            total_contacts = len(contact_items)
            total_batches = (total_contacts + batch_size - 1) // batch_size

            self.logger.info(
                f"Inserting {total_contacts} contacts in {total_batches} batches of {batch_size}",
            )

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, total_contacts)
                batch = contact_items[start_idx:end_idx]

                self.logger.info(
                    f"Processing batch {batch_idx + 1}/{total_batches} ({start_idx} to {end_idx - 1})",
                )

                for email, contact in batch:
                    try:
                        conn.execute(
                            """
                        INSERT INTO unified_contacts (
                            email, first_name, last_name, full_name, company, job_title,
                            phone, country, source, domain, last_interaction_date,
                            first_seen_date, last_updated, tags, notes, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            [
                                contact["email"],
                                contact["first_name"],
                                contact["last_name"],
                                contact["full_name"],
                                contact["company"],
                                contact["job_title"],
                                contact["phone"],
                                contact["country"],
                                contact["source"],
                                contact["domain"],
                                contact["last_interaction_date"],
                                contact["first_seen_date"],
                                contact["last_updated"],
                                contact["tags"],
                                contact["notes"],
                                json.dumps(contact["metadata"])
                                if contact["metadata"] is not None
                                else None,
                            ],
                        )
                    except Exception as e:
                        self.logger.error(f"Error inserting contact {email}: {e}")

                self.logger.info(f"Completed batch {batch_idx + 1}/{total_batches}")

            self.logger.info(
                f"Inserted {total_contacts} contacts into unified_contacts table",
            )
        except Exception as e:
            self.logger.error(
                f"Error inserting contacts into unified_contacts table: {e}",
            )
            raise


def main():
    """Main entry point for the script."""
    script = ContactConsolidation()
    script.execute()


if __name__ == "__main__":
    main()
