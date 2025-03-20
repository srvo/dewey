#!/usr/bin/env python3
"""
Contact Consolidation Script
===========================

This script consolidates contact information from various tables in the MotherDuck database
into a single unified_contacts table, focusing on individuals.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

import duckdb

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection, get_motherduck_connection


class ContactConsolidation(BaseScript):
    """
    Consolidates contact information from various sources into a unified table.
    """

    def __init__(self) -> None:
        """Initializes the ContactConsolidation script."""
        super().__init__(config_section='contact_consolidation', requires_db=True)

    def create_unified_contacts_table(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Create the unified_contacts table if it doesn't exist.

        Args:
            conn: DuckDB connection
        """
        try:
            conn.execute("""
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
            """)
            self.logger.info("Created or verified unified_contacts table")
        except Exception as e:
            self.logger.error(f"Error creating unified_contacts table: {e}")
            raise

    def extract_contacts_from_crm(self, conn: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
        """Extract contacts from CRM-related tables.

        Args:
            conn: DuckDB connection

        Returns:
            List of contact dictionaries
        """
        try:
            # We'll use crm_contacts as the primary source since all three CRM tables have the same schema
            result = conn.execute("""
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
                source,
                domain,
                event_time as last_interaction_date,
                event_time as first_seen_date,
                last_updated,
                NULL as tags,
                event_summary as notes,
                NULL as metadata
            FROM crm_contacts
            """).fetchall()

            contacts = []
            for row in result:
                contact = {
                    'email': row[0],
                    'full_name': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'company': row[4],
                    'job_title': row[5],
                    'phone': row[6],
                    'country': row[7],
                    'source': row[8],
                    'domain': row[9],
                    'last_interaction_date': row[10],
                    'first_seen_date': row[11],
                    'last_updated': row[12],
                    'tags': row[13],
                    'notes': row[14],
                    'metadata': row[15]
                }
                contacts.append(contact)

            self.logger.info(f"Extracted {len(contacts)} contacts from CRM tables")
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from CRM tables: {e}")
            return []

    def extract_contacts_from_emails(self, conn: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
        """Extract contacts from email-related tables.

        Args:
            conn: DuckDB connection

        Returns:
            List of contact dictionaries
        """
        try:
            # Extract from crm_emails
            result = conn.execute("""
            SELECT DISTINCT
                from_email as email,
                from_name as full_name,
                CASE 
                    WHEN POSITION(' ' IN from_name) > 0 
                    THEN TRIM(SUBSTR(from_name, 1, POSITION(' ' IN from_name) - 1)) 
                    ELSE from_name 
                END as first_name,
                CASE 
                    WHEN POSITION(' ' IN from_name) > 0 
                    THEN TRIM(SUBSTR(from_name, POSITION(' ' IN from_name) + 1)) 
                    ELSE NULL 
                END as last_name,
                NULL as company,
                NULL as job_title,
                NULL as phone,
                NULL as country,
                'email' as source,
                SUBSTR(from_email, POSITION('@' IN from_email) + 1) as domain,
                date as last_interaction_date,
                date as first_seen_date,
                date as last_updated,
                NULL as tags,
                subject as notes,
                NULL as metadata
            FROM crm_emails
            WHERE from_email IS NOT NULL AND from_email != ''
            """).fetchall()

            contacts = []
            for row in result:
                contact = {
                    'email': row[0],
                    'full_name': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'company': row[4],
                    'job_title': row[5],
                    'phone': row[6],
                    'country': row[7],
                    'source': row[8],
                    'domain': row[9],
                    'last_interaction_date': row[10],
                    'first_seen_date': row[11],
                    'last_updated': row[12],
                    'tags': row[13],
                    'notes': row[14],
                    'metadata': row[15]
                }
                contacts.append(contact)

            # Extract from activedata_email_analyses
            result = conn.execute("""
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
            FROM activedata_email_analyses
            WHERE from_address IS NOT NULL AND from_address != ''
            """).fetchall()

            for row in result:
                contact = {
                    'email': row[0],
                    'full_name': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'company': row[4],
                    'job_title': row[5],
                    'phone': row[6],
                    'country': row[7],
                    'source': row[8],
                    'domain': row[9],
                    'last_interaction_date': row[10],
                    'first_seen_date': row[11],
                    'last_updated': row[12],
                    'tags': row[13],
                    'notes': row[14],
                    'metadata': row[15]
                }
                contacts.append(contact)

            self.logger.info(f"Extracted {len(contacts)} contacts from email tables")
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from email tables: {e}")
            return []

    def extract_contacts_from_subscribers(self, conn: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
        """Extract contacts from subscriber-related tables.

        Args:
            conn: DuckDB connection

        Returns:
            List of contact dictionaries
        """
        try:
            # Extract from input_data_subscribers
            result = conn.execute("""
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
            FROM input_data_subscribers
            WHERE email IS NOT NULL AND email != ''
            """).fetchall()

            contacts = []
            for row in result:
                contact = {
                    'email': row[0],
                    'full_name': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'company': row[4],
                    'job_title': row[5],
                    'phone': row[6],
                    'country': row[7],
                    'source': row[8],
                    'domain': row[9],
                    'last_interaction_date': row[10],
                    'first_seen_date': row[11],
                    'last_updated': row[12],
                    'tags': row[13],
                    'notes': row[14],
                    'metadata': row[15]
                }
                contacts.append(contact)

            # Extract from input_data_EIvirgin_csvSubscribers
            # This table has a complex schema, so we'll extract what we can
            result = conn.execute("""
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
            """).fetchall()

            for row in result:
                contact = {
                    'email': row[0],
                    'full_name': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'company': row[4],
                    'job_title': row[5],
                    'phone': row[6],
                    'country': row[7],
                    'source': row[8],
                    'domain': row[9],
                    'last_interaction_date': row[10],
                    'first_seen_date': row[11],
                    'last_updated': row[12],
                    'tags': row[13],
                    'notes': row[14],
                    'metadata': row[15]
                }
                contacts.append(contact)

            self.logger.info(f"Extracted {len(contacts)} contacts from subscriber tables")
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from subscriber tables: {e}")
            return []

    def extract_contacts_from_blog_signups(self, conn: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
        """Extract contacts from blog signup form responses.

        Args:
            conn: DuckDB connection

        Returns:
            List of contact dictionaries
        """
        try:
            result = conn.execute("""
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
            """).fetchall()

            contacts = []
            for row in result:
                contact = {
                    'email': row[0],
                    'full_name': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'company': row[4],
                    'job_title': row[5],
                    'phone': row[6],
                    'country': row[7],
                    'source': row[8],
                    'domain': row[9],
                    'last_interaction_date': row[10],
                    'first_seen_date': row[11],
                    'last_updated': row[12],
                    'tags': row[13],
                    'notes': row[14],
                    'metadata': row[15]
                }
                contacts.append(contact)

            self.logger.info(f"Extracted {len(contacts)} contacts from blog signup form responses")
            return contacts
        except Exception as e:
            self.logger.error(f"Error extracting contacts from blog signup form responses: {e}")
            return []

    def merge_contacts(self, contacts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Merge contacts by email, prioritizing more complete information.

        Args:
            contacts: List of contact dictionaries

        Returns:
            Dictionary of merged contacts keyed by email
        """
        merged_contacts = {}

        for contact in contacts:
            email = contact['email']
            if not email:
                continue

            email = email.lower().strip()

            if email not in merged_contacts:
                merged_contacts[email] = contact
                continue

            # Merge with existing contact, prioritizing non-null values
            existing = merged_contacts[email]
            for key, value in contact.items():
                if key == 'email':
                    continue

                # For all other fields, prefer non-null values
                if value is not None and existing[key] is None:
                    existing[key] = value

        self.logger.info(f"Merged contacts into {len(merged_contacts)} unique contacts")
        return merged_contacts

    def insert_unified_contacts(self, conn: duckdb.DuckDBPyConnection, contacts: Dict[str, Dict[str, Any]]) -> None:
        """Insert merged contacts into the unified_contacts table.

        Args:
            conn: DuckDB connection
            contacts: Dictionary of merged contacts keyed by email
        """
        try:
            # Clear existing data
            conn.execute("DELETE FROM unified_contacts")
            self.logger.info("Cleared existing data from unified_contacts table")

            # Insert new data in batches
            batch_size = int(self.get_config_value('batch_size', 100))
            contact_items = list(contacts.items())
            total_contacts = len(contact_items)
            total_batches = (total_contacts + batch_size - 1) // batch_size

            self.logger.info(f"Inserting {total_contacts} contacts in {total_batches} batches of {batch_size}")

            for batch_idx in range(0, total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, total_contacts)
                batch = contact_items[start_idx:end_idx]

                self.logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({start_idx} to {end_idx - 1})")

                for email, contact in batch:
                    try:
                        conn.execute("""
                        INSERT INTO unified_contacts (
                            email, first_name, last_name, full_name, company, job_title, 
                            phone, country, source, domain, last_interaction_date, 
                            first_seen_date, last_updated, tags, notes, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, [
                            contact['email'],
                            contact['first_name'],
                            contact['last_name'],
                            contact['full_name'],
                            contact['company'],
                            contact['job_title'],
                            contact['phone'],
                            contact['country'],
                            contact['source'],
                            contact['domain'],
                            contact['last_interaction_date'],
                            contact['first_seen_date'],
                            contact['last_updated'],
                            contact['tags'],
                            contact['notes'],
                            json.dumps(contact['metadata']) if contact['metadata'] is not None else None
                        ])
                    except Exception as e:
                        self.logger.error(f"Error inserting contact {email}: {e}")

                self.logger.info(f"Completed batch {batch_idx + 1}/{total_batches}")

            self.logger.info(f"Inserted {total_contacts} contacts into unified_contacts table")
        except Exception as e:
            self.logger.error(f"Error inserting contacts into unified_contacts table: {e}")
            raise

    def run(self) -> None:
        """Main function to consolidate contacts."""
        database_name = self.get_config_value('database', 'dewey')

        try:
            # Connect to MotherDuck
            conn = self.db_conn.connection  # Access the DuckDB connection from DatabaseConnection

            # Create unified_contacts table
            self.create_unified_contacts_table(conn)

            # Extract contacts from various sources
            crm_contacts = self.extract_contacts_from_crm(conn)
            email_contacts = self.extract_contacts_from_emails(conn)
            subscriber_contacts = self.extract_contacts_from_subscribers(conn)
            blog_signup_contacts = self.extract_contacts_from_blog_signups(conn)

            # Combine all contacts
            all_contacts = crm_contacts + email_contacts + subscriber_contacts + blog_signup_contacts
            self.logger.info(f"Total contacts extracted: {len(all_contacts)}")

            # Merge contacts
            merged_contacts = self.merge_contacts(all_contacts)

            # Insert into unified_contacts table
            self.insert_unified_contacts(conn, merged_contacts)

            self.logger.info("Contact consolidation completed successfully")

        except Exception as e:
            self.logger.error(f"Error in contact consolidation: {e}")
            sys.exit(1)


def main():
    """Main entry point for the script."""
    script = ContactConsolidation()
    script.execute()


if __name__ == "__main__":
    main()
