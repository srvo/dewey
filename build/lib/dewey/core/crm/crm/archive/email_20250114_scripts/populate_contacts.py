"""populate_contacts.py - Contact Management and Import System

This module handles the import, processing, and management of contact data from multiple sources:
- Email databases
- CSV files (Data Master, subscribers, exported contacts)
- SQLite databases

Key Features:
- Automatic contact extraction from email data
- Multi-source contact import with deduplication
- Priority scoring based on contact type and engagement
- Comprehensive logging and error handling
- Data validation and normalization
- Summary reporting and statistics

The system maintains a central contacts database that serves as the source of truth
for all contact-related operations in the application.
"""

import csv
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

# Configure application-wide logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            "project.log", mode="a"
        ),  # Append mode for continuous logging
    ],
)

logger = logging.getLogger("contacts_import")


def extract_domain(email: str) -> str:
    """Extract and normalize the domain portion from an email address.

    Args:
    ----
        email (str): The email address to process

    Returns:
    -------
        str: The domain portion in lowercase, or empty string if invalid

    Example:
    -------
        >>> extract_domain("john.doe@example.com")
        'example.com'

    """
    try:
        return email.split("@")[1].lower() if "@" in email else ""
    except:
        return ""


def extract_contacts_from_emails(db_path: str = "email_data.db") -> None:
    """Extract unique contacts from email database and populate contacts table.

    Processes email data to:
    - Identify unique senders
    - Calculate email statistics (count, average priority)
    - Track last interaction date
    - Extract domain information

    Args:
    ----
        db_path (str): Path to SQLite database containing email data

    Raises:
    ------
        sqlite3.Error: If database operations fail
        Exception: For any other unexpected errors

    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get unique senders and their email counts
        cursor.execute(
            """
            WITH email_stats AS (
                SELECT
                    from_email,
                    from_name,
                    COUNT(*) as email_count,
                    AVG(CASE
                        WHEN current_priority IS NOT NULL THEN current_priority
                        ELSE 0
                    END) as avg_priority,
                    MAX(date) as last_email,
                    CASE
                        WHEN from_email LIKE '%@%'
                        THEN LOWER(SUBSTR(from_email, INSTR(from_email, '@') + 1))
                        ELSE ''
                    END as domain
                FROM emails
                WHERE from_email IS NOT NULL
                GROUP BY from_email, from_name
            )
            INSERT OR REPLACE INTO contacts (
                email,
                name,
                domain,
                avg_priority,
                email_count,
                last_priority_change
            )
            SELECT
                from_email,
                from_name,
                domain,
                avg_priority,
                email_count,
                last_email
            FROM email_stats
        """
        )

        count = cursor.rowcount
        conn.commit()
        logger.info(f"Extracted {count} unique contacts from emails")

    except Exception as e:
        logger.error(f"Error extracting contacts: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_priority_from_type(contact_type: str, tags: str = "") -> int:
    """Calculate contact priority score based on type and tags.

    Priority levels:
    5 - Clients and client households
    4 - Active prospects, advisers, supporters
    3 - Media and institutional contacts
    1 - All others

    Args:
    ----
        contact_type (str): Contact type classification
        tags (str): Optional tags for additional context

    Returns:
    -------
        int: Priority score between 1-5

    Example:
    -------
        >>> get_priority_from_type("Client", "VIP")
        5

    """
    if not contact_type:
        return 0

    contact_type = contact_type.lower()
    tags = tags.lower() if tags else ""

    # Highest priority for clients
    if "client" in contact_type or "client household" in contact_type:
        return 5
    # High priority for active prospects, advisers, supporters and helpers
    elif "prospect" in contact_type and "dropped" not in tags:
        return 4
    elif "adviser" in contact_type:
        return 4
    elif "supporter" in contact_type or "helper" in contact_type:
        return 4
    # Medium priority for media and institutional contacts
    elif "media" in contact_type or "institutional" in contact_type:
        return 3
    return 1


def import_data_master_contacts(csv_path: str, db_path: str = "email_data.db") -> None:
    """Import contacts from Data Master CSV file.

    Handles:
    - CSV parsing and validation
    - Name normalization
    - Priority calculation
    - Domain extraction
    - Database insertion with deduplication

    Args:
    ----
        csv_path (str): Path to Data Master CSV file
        db_path (str): Path to target SQLite database

    Raises:
    ------
        FileNotFoundError: If CSV file doesn't exist
        csv.Error: If CSV parsing fails
        sqlite3.Error: If database operations fail

    """
    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("Email", "").strip().lower()
                if not email or "@" not in email:
                    continue

                name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                contact_type = row.get("Entity Record Type", "")

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO contacts (
                        email,
                        name,
                        domain,
                        avg_priority,
                        email_count,
                        last_priority_change
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        email,
                        name,
                        extract_domain(email),
                        get_priority_from_type(contact_type),
                        0,  # Will update count later
                        datetime.now(),
                    ),
                )

        count = cursor.rowcount
        conn.commit()
        logger.info(f"Imported {count} contacts from Data Master CSV")

    except Exception as e:
        logger.error(f"Error importing Data Master contacts: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def import_subscribers(csv_path: str, db_path: str = "email_data.db") -> None:
    """Import and process subscriber data from CSV.

    Special handling for:
    - Engagement metrics (opens, clicks)
    - Sent count tracking
    - JSON attribute parsing
    - Priority adjustment based on engagement

    Args:
    ----
        csv_path (str): Path to subscribers CSV file
        db_path (str): Path to target SQLite database

    Raises:
    ------
        FileNotFoundError: If CSV file doesn't exist
        json.JSONDecodeError: If attribute parsing fails
        sqlite3.Error: If database operations fail

    """
    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email", "").strip().lower()
                if not email or "@" not in email:
                    continue

                # Parse attributes JSON string
                try:
                    attributes = json.loads(row.get("attributes", "{}"))
                except:
                    attributes = {}

                # Calculate engagement score (0-5) based on opens and clicks
                opens = float(attributes.get("Opens", 0) or 0)
                if str(opens).lower() == "nan":
                    opens = 0

                clicks = float(attributes.get("Clicks", 0) or 0)
                if str(clicks).lower() == "nan":
                    clicks = 0

                engagement_score = min(5, ((opens / 10) + (clicks / 2)))

                # Handle sent count
                sent = attributes.get("Sent", 0) or 0
                if str(sent).lower() == "nan":
                    sent = 0
                sent_count = int(float(sent))

                cursor.execute(
                    """
                    UPDATE contacts
                    SET email_count = email_count + ?,
                        avg_priority = CASE
                            WHEN avg_priority < ? THEN ?
                            ELSE avg_priority
                        END
                    WHERE email = ?
                """,
                    (sent_count, engagement_score, engagement_score, email),
                )

                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO contacts (
                            email,
                            name,
                            domain,
                            avg_priority,
                            email_count,
                            last_priority_change
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            email,
                            row.get("name", ""),
                            extract_domain(email),
                            engagement_score,
                            sent_count,
                            datetime.now(),
                        ),
                    )

        count = cursor.rowcount
        conn.commit()
        logger.info(f"Imported {count} contacts from subscribers CSV")

    except Exception as e:
        logger.error(f"Error importing subscribers: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def import_exported_contacts(csv_path: str, db_path: str = "email_data.db") -> None:
    """Import contacts from exported contacts CSV file.

    Handles multiple email fields:
    - primary_email
    - work_email
    - personal_email
    - other_email

    Processes:
    - Name normalization
    - Type and tag parsing
    - Priority calculation
    - Domain extraction

    Args:
    ----
        csv_path (str): Path to exported contacts CSV
        db_path (str): Path to target SQLite database

    Raises:
    ------
        FileNotFoundError: If CSV file doesn't exist
        csv.Error: If CSV parsing fails
        sqlite3.Error: If database operations fail

    """
    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check all possible email fields
                emails = [
                    row.get("primary_email", ""),
                    row.get("work_email", ""),
                    row.get("personal_email", ""),
                    row.get("other_email", ""),
                ]

                # Process each email for the contact
                for email in emails:
                    email = email.strip().lower()
                    if not email or "@" not in email:
                        continue

                    name = row.get("name", "")
                    contact_type = row.get("type", "")
                    tags = row.get("tags", "")

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO contacts (
                            email,
                            name,
                            domain,
                            avg_priority,
                            email_count,
                            last_priority_change
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            email,
                            name,
                            extract_domain(email),
                            get_priority_from_type(contact_type, tags),
                            0,  # Will update count later
                            datetime.now(),
                        ),
                    )

        count = cursor.rowcount
        conn.commit()
        logger.info(f"Imported {count} contacts from exported contacts CSV")

    except Exception as e:
        logger.error(f"Error importing exported contacts: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def summarize_contacts(db_path: str = "email_data.db") -> None:
    """Generate and display summary statistics for contacts database.

    Reports:
    - Total contact count
    - Top domains by contact count
    - Priority level distribution

    Args:
    ----
        db_path (str): Path to SQLite database

    Raises:
    ------
        sqlite3.Error: If database operations fail

    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get total contacts
        cursor.execute("SELECT COUNT(*) FROM contacts")
        total = cursor.fetchone()[0]

        # Get top domains
        cursor.execute(
            """
            SELECT domain, COUNT(*) as count
            FROM contacts
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 5
        """
        )
        top_domains = cursor.fetchall()

        # Get priority distribution
        cursor.execute(
            """
            SELECT
                ROUND(avg_priority) as priority_level,
                COUNT(*) as count
            FROM contacts
            WHERE avg_priority IS NOT NULL
            GROUP BY priority_level
            ORDER BY priority_level
        """
        )
        priority_dist = cursor.fetchall()

        print("\nContacts Summary:")
        print(f"Total Contacts: {total}")

        print("\nTop Domains:")
        for domain, count in top_domains:
            print(f"  {domain}: {count}")

        print("\nPriority Distribution:")
        for priority, count in priority_dist:
            print(f"  Priority {priority}: {count}")

    except Exception as e:
        logger.error(f"Error summarizing contacts: {str(e)}")
        raise
    finally:
        conn.close()


def import_from_sqlite_db(db_path: str, target_db: str = "email_data.db") -> None:
    """Import contacts from another SQLite database.

    Features:
    - Automatic table detection
    - Column name inference
    - Data normalization
    - Deduplication

    Args:
    ----
        db_path (str): Path to source SQLite database
        target_db (str): Path to target SQLite database

    Raises:
    ------
        FileNotFoundError: If source database doesn't exist
        sqlite3.Error: If database operations fail

    """
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return

    source_conn = sqlite3.connect(db_path)
    target_conn = sqlite3.connect(target_db)
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    try:
        # Check if the source has a contacts table
        source_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%contact%'"
        )
        contact_tables = source_cursor.fetchall()

        if not contact_tables:
            logger.info(f"No contact tables found in {db_path}")
            return

        for table in contact_tables:
            table_name = table[0]
            # Get column names
            source_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = source_cursor.fetchall()

            # Look for email and name columns
            email_col = next(
                (col[1] for col in columns if "email" in col[1].lower()), None
            )
            name_col = next(
                (col[1] for col in columns if "name" in col[1].lower()), None
            )

            if not email_col:
                continue

            # Get the data
            source_cursor.execute(
                f"SELECT {email_col}, {name_col or 'NULL'} FROM {table_name}"
            )
            contacts = source_cursor.fetchall()

            for contact in contacts:
                email = contact[0]
                if not email or "@" not in str(email):
                    continue

                name = contact[1] if contact[1] != "NULL" else ""

                target_cursor.execute(
                    """
                    INSERT OR REPLACE INTO contacts (
                        email,
                        name,
                        domain,
                        avg_priority,
                        email_count,
                        last_priority_change
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(email).lower().strip(),
                        str(name).strip(),
                        extract_domain(email),
                        0,  # Default priority
                        0,  # Will update count later
                        datetime.now(),
                    ),
                )

        count = target_cursor.rowcount
        target_conn.commit()
        logger.info(f"Imported {count} contacts from {db_path}")

    except Exception as e:
        logger.error(f"Error importing from {db_path}: {str(e)}")
        target_conn.rollback()
        raise
    finally:
        source_conn.close()
        target_conn.close()


def main() -> None:
    """Main execution function for contact population system.

    Orchestrates:
    - Contact extraction from email data
    - CSV file processing
    - Database imports
    - Summary reporting
    - File cleanup

    Workflow:
    1. Extract contacts from email database
    2. Process all configured CSV files
    3. Import from additional SQLite databases
    4. Generate summary report
    5. Clean up processed files

    Raises:
    ------
        Exception: For any unexpected errors during execution

    """
    try:
        # Extract contacts from existing email data
        extract_contacts_from_emails()

        # Import from various sources
        csv_files = [
            "Data Master - Contact.csv",
            "DB - Contacts (1).csv",
            "EI Subscribers.xlsx - sheet.csv",
            "email_analysis_results.csv",
            "subscribers.csv",
            "export-contacts-a34bdf1541507a026ccea1d88db93577-12- 6-23-09-10pm.csv",
        ]

        # Additional database files
        db_files = ["contacts.db", "calendar_data.db", "zoommeeting.enc.db"]

        # Process CSV files
        for file in csv_files:
            if Path(file).exists():
                logger.info(f"Processing {file}")
                if "Data Master" in file:
                    import_data_master_contacts(file)
                elif "subscribers" in file.lower() or "EI Subscribers" in file:
                    import_subscribers(file)
                else:
                    import_exported_contacts(file)

                # Delete the file after successful import
                Path(file).unlink()
                logger.info(f"Deleted {file}")

        # Process database files
        for db_file in db_files:
            if Path(db_file).exists():
                logger.info(f"Processing {db_file}")
                import_from_sqlite_db(db_file)
                # Don't delete database files automatically

        # Display summary
        summarize_contacts()

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
