#!/usr/bin/env python3
"""Enhanced Email Sync Script.

This script extends the functionality of the original sync_script.py by adding:
- Contact extraction and management
- Calendar event extraction and processing
- Metadata database for advanced features
- Abstraction layer for email providers

This script integrates features from both the original email sync service
and the email-service repository.

Usage:
    python extended_sync.py [--config .env] [--metadata-db /data/metadata.db]
"""
from __future__ import annotations

import argparse
import datetime
import email
import imaplib
import json
import logging
import os
import re
import sqlite3
import ssl
import time
from email.header import decode_header
from typing import NoReturn

import icalendar
from email_validator import EmailNotValidError, validate_email

# Import our new modules
# We use try/except to allow the script to run even if these modules aren't yet available
try:
    from scripts.calendar_processor import CalendarEventProcessor
    from scripts.contact_extractor import ContactExtractor

    METADATA_ENABLED = True
except ImportError:
    logging.warning("Metadata modules not found, running in basic mode")
    METADATA_ENABLED = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_CONFIG = {
    "IMAP_SERVER": "your-imap-server.com",
    "EMAIL_USER": "user@example.com",
    "EMAIL_PASSWORD": "password",
    "EXCLUDE_FOLDERS": ["[Gmail]/Spam", "[Gmail]/Trash"],
    "DB_PATH": "/data/emails.db",
    "METADATA_DB_PATH": "/data/metadata.db",
    "CONNECTION_TIMEOUT": 30,
    "MAX_RETRIES": 5,
    "RETRY_DELAY": 60,
    "SYNC_INTERVAL": 300,  # 5 minutes
    "ENABLE_METADATA": True,
    "EXTRACT_CALENDAR_EVENTS": True,
    "EXTRACT_CONTACTS": True,
}


class EmailProvider:
    """Base interface for email providers."""

    def connect(self) -> NoReturn:
        """Establish connection to email provider."""
        raise NotImplementedError

    def list_folders(self) -> NoReturn:
        """List available folders/labels."""
        raise NotImplementedError

    def get_emails(self, folder, since=None, limit=None) -> NoReturn:
        """Get emails from specified folder."""
        raise NotImplementedError

    def get_email_content(self, email_id, folder) -> NoReturn:
        """Get full content of an email."""
        raise NotImplementedError

    def close(self) -> NoReturn:
        """Close connection to email provider."""
        raise NotImplementedError


class ImapEmailProvider(EmailProvider):
    """Implementation for IMAP providers."""

    def __init__(self, server, username, password, timeout=30) -> None:
        self.server = server
        self.username = username
        self.password = password
        self.timeout = timeout
        self.connection = None

    def connect(self):
        """Establish IMAP connection."""
        retry_count = 0
        max_retries = int(os.getenv("MAX_RETRIES", "5"))
        retry_delay = int(os.getenv("RETRY_DELAY", "60"))

        while retry_count < max_retries:
            try:
                logger.info(f"Establishing IMAP connection to {self.server}")
                self.connection = imaplib.IMAP4_SSL(self.server, timeout=self.timeout)
                self.connection.login(self.username, self.password)
                logger.info("Successfully connected to IMAP server")
                return self.connection
            except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
                retry_count += 1
                logger.exception(
                    f"Connection attempt {retry_count} failed: {e!s}. Retrying in {retry_delay} seconds...",
                )
                time.sleep(retry_delay)

        logger.critical(
            f"Failed to connect to IMAP server after {max_retries} attempts. Exiting.",
        )
        msg = f"Could not connect to IMAP server {self.server} after {max_retries} attempts"
        raise ConnectionError(msg)

    def check_connection(self):
        """Check if the connection is still alive and reconnect if necessary."""
        if not self.connection:
            return self.connect()

        try:
            # Simple NOOP command to check connection
            status, response = self.connection.noop()
            if status == "OK":
                return self.connection
        except (OSError, ssl.SSLError, imaplib.IMAP4.error) as e:
            logger.warning(f"IMAP connection lost: {e!s}. Reconnecting...")

        # If we got here, connection needs to be re-established
        try:
            self.connection.logout()
        except:
            pass  # Ignore errors during logout of dead connection

        return self.connect()

    def list_folders(self):
        """List available folders/labels."""
        self.check_connection()
        status, folder_list = self.connection.list()

        if status != "OK":
            logger.error("Failed to retrieve folder list")
            return []

        folders = []
        for folder_data in folder_list:
            parts = folder_data.decode().split(' "', 1)
            if len(parts) > 1:
                folder = parts[1].strip('"')
                folders.append(folder)

        return folders

    def get_emails(self, folder, since=None, limit=None):
        """Get email IDs from specified folder.

        Args:
        ----
            folder: Mailbox folder name
            since: Optional date to get emails since (yyyy-mm-dd format)
            limit: Optional maximum number of emails to return

        Returns:
        -------
            list: List of email IDs

        """
        self.check_connection()

        # Select the mailbox
        status, data = self.connection.select(f'"{folder}"', readonly=True)
        if status != "OK":
            logger.error(f"Failed to select folder: {folder}")
            return []

        # Build search criteria
        search_criteria = "ALL"
        if since:
            try:
                date_obj = datetime.datetime.strptime(since, "%Y-%m-%d")
                date_str = date_obj.strftime("%d-%b-%Y")
                search_criteria = f'(SINCE "{date_str}")'
            except ValueError:
                logger.warning(f"Invalid date format: {since}. Using ALL criteria.")

        # Search for messages
        status, data = self.connection.search(None, search_criteria)
        if status != "OK":
            logger.error(f"Failed to search for messages in {folder}")
            return []

        # Get the list of email IDs
        email_ids = data[0].split()

        # Apply limit if specified
        if limit and len(email_ids) > limit:
            email_ids = email_ids[-limit:]  # Get the most recent emails

        return [id.decode() for id in email_ids]

    def get_email_content(self, email_id, folder=None):
        """Get full content of an email.

        Args:
        ----
            email_id: Email ID to fetch
            folder: Optional folder name if not already selected

        Returns:
        -------
            tuple: (email_data, raw_email) or (None, None) on error

        """
        self.check_connection()

        # Select the folder if specified
        if folder:
            status, data = self.connection.select(f'"{folder}"', readonly=True)
            if status != "OK":
                logger.error(f"Failed to select folder: {folder}")
                return None, None

        # Fetch the email
        try:
            status, data = self.connection.fetch(email_id, "(RFC822 UID)")
            if status != "OK":
                logger.error(f"Failed to fetch email {email_id}")
                return None, None

            # Extract UID from the response
            for response_part in data:
                if isinstance(response_part, tuple):
                    uid = None
                    # Parse the UID
                    pattern = re.compile(r"UID (\d+)")
                    match = pattern.search(
                        response_part[0].decode("utf-8", errors="ignore"),
                    )
                    if match:
                        uid = match.group(1)

                    # Get raw email data
                    raw_email = response_part[1]

                    return uid, raw_email

            logger.error(f"Failed to extract UID and content for email {email_id}")
            return None, None
        except Exception as e:
            logger.exception(f"Error fetching email {email_id}: {e!s}")
            return None, None

    def close(self) -> None:
        """Close connection to email provider."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                self.connection = None
                logger.info("IMAP connection closed")
            except Exception as e:
                logger.warning(f"Error closing IMAP connection: {e!s}")


class EmailSyncService:
    """Main service for email synchronization with metadata."""

    def __init__(self, config=None) -> None:
        """Initialize the sync service.

        Args:
        ----
            config: Optional configuration dictionary or path to config file

        """
        # Load config
        self.config = self._load_config(config)

        # Setup email provider
        self._setup_email_provider()

        # Initialize databases
        self._init_databases()

        # Initialize metadata processing if enabled
        if self.config.get("ENABLE_METADATA", True) and METADATA_ENABLED:
            self._init_metadata_processors()

    def _load_config(self, config=None):
        """Load configuration from various sources.

        Args:
        ----
            config: Config dict or path to config file

        Returns:
        -------
            dict: Configuration dictionary

        """
        # Start with default config
        result = DEFAULT_CONFIG.copy()

        # Override with environment variables
        for key in result:
            if key in os.environ:
                result[key] = os.environ[key]

                # Handle boolean values
                if result[key].lower() in ("true", "yes", "1"):
                    result[key] = True
                elif result[key].lower() in ("false", "no", "0"):
                    result[key] = False

                # Handle list values
                if key == "EXCLUDE_FOLDERS" and isinstance(result[key], str):
                    result[key] = result[key].split(",")

        # Override with config file or dict
        if config:
            if isinstance(config, str):
                # Config is a file path
                try:
                    with open(config) as f:
                        file_config = json.load(f)
                        result.update(file_config)
                except Exception as e:
                    logger.exception(f"Error loading config file {config}: {e!s}")
            elif isinstance(config, dict):
                # Config is a dictionary
                result.update(config)

        # Process special values
        if "EMAIL_PASSWORD" in result:
            password = result["EMAIL_PASSWORD"]
            # Handle potential quotes in password string
            if (password.startswith('"') and password.endswith('"')) or (
                password.startswith("'") and password.endswith("'")
            ):
                result["EMAIL_PASSWORD"] = password[1:-1]

        # Convert string values to appropriate types
        if "CONNECTION_TIMEOUT" in result:
            result["CONNECTION_TIMEOUT"] = int(result["CONNECTION_TIMEOUT"])
        if "MAX_RETRIES" in result:
            result["MAX_RETRIES"] = int(result["MAX_RETRIES"])
        if "RETRY_DELAY" in result:
            result["RETRY_DELAY"] = int(result["RETRY_DELAY"])
        if "SYNC_INTERVAL" in result:
            result["SYNC_INTERVAL"] = int(result["SYNC_INTERVAL"])

        # Log configuration (mask password)
        password = result["EMAIL_PASSWORD"]
        logger.info(
            f"Email config - Server: {result['IMAP_SERVER']}, User: {result['EMAIL_USER']}, "
            f"Pass: {password[:2]}***{password[-2:]} (length: {len(password)})",
        )

        return result

    def _setup_email_provider(self) -> None:
        """Initialize the email provider based on configuration."""
        self.email_provider = ImapEmailProvider(
            server=self.config["IMAP_SERVER"],
            username=self.config["EMAIL_USER"],
            password=self.config["EMAIL_PASSWORD"],
            timeout=self.config["CONNECTION_TIMEOUT"],
        )

    def _init_databases(self) -> None:
        """Initialize the databases."""
        # Initialize emails database
        self.emails_db_path = self.config["DB_PATH"]
        self._init_emails_database()

        # Initialize metadata database if enabled
        if self.config.get("ENABLE_METADATA", True):
            self.metadata_db_path = self.config["METADATA_DB_PATH"]
            # Only initialize if the metadata module is available
            if METADATA_ENABLED:
                self._init_metadata_database()

    def _init_emails_database(self) -> None:
        """Initialize the emails database."""
        try:
            # Ensure directory exists
            db_dir = os.path.dirname(self.emails_db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            conn = sqlite3.connect(self.emails_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY,
                    uid TEXT UNIQUE,
                    sender TEXT,
                    recipient TEXT,
                    cc TEXT,
                    subject TEXT,
                    body TEXT,
                    raw_body TEXT,
                    folder TEXT,
                    labels TEXT,
                    annotations TEXT,
                    date TEXT
                )
            """,
            )
            conn.commit()
            conn.close()
            logger.info(f"Emails database initialized at {self.emails_db_path}")
        except Exception as e:
            logger.exception(f"Error initializing emails database: {e!s}")
            raise

    def _init_metadata_database(self) -> None:
        """Initialize or verify the metadata database."""
        try:
            # If init_metadata_db.py script exists, use it
            metadata_init_script = os.path.join("scripts", "init_metadata_db.py")
            if os.path.exists(metadata_init_script):
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "init_metadata_db",
                    metadata_init_script,
                )
                init_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(init_module)
                init_module.setup_metadata_database(self.metadata_db_path)
                logger.info(
                    f"Metadata database initialized using init_metadata_db.py at {self.metadata_db_path}",
                )
            else:
                # Fallback to basic initialization
                conn = sqlite3.connect(self.metadata_db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS contacts (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT,
                        domain TEXT,
                        email_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)",
                )
                conn.commit()
                conn.close()
                logger.info(
                    f"Basic metadata database initialized at {self.metadata_db_path}",
                )
        except Exception as e:
            logger.exception(f"Error initializing metadata database: {e!s}")
            logger.warning("Continuing without metadata support")
            self.config["ENABLE_METADATA"] = False

    def _init_metadata_processors(self) -> None:
        """Initialize metadata processors if enabled."""
        try:
            # Initialize contact extractor
            if self.config.get("EXTRACT_CONTACTS", True):
                self.contact_extractor = ContactExtractor(db_path=self.metadata_db_path)
                logger.info("Contact extractor initialized")
            else:
                self.contact_extractor = None

            # Initialize calendar processor
            if self.config.get("EXTRACT_CALENDAR_EVENTS", True):
                # Try to import calendar processor
                try:
                    self.calendar_processor = CalendarEventProcessor(
                        db_path=self.metadata_db_path,
                    )
                    logger.info("Calendar processor initialized")
                except (ImportError, NameError):
                    logger.warning("Calendar processor module not found")
                    self.calendar_processor = None
            else:
                self.calendar_processor = None
        except Exception as e:
            logger.exception(f"Error initializing metadata processors: {e!s}")
            logger.warning("Continuing without metadata processors")
            self.contact_extractor = None
            self.calendar_processor = None

    def sync_emails(self) -> bool | None:
        """Synchronize emails from all folders."""
        try:
            # Connect to email provider
            self.email_provider.connect()

            # Get list of folders
            folders = self.email_provider.list_folders()
            logger.info(f"Found {len(folders)} folders")

            # Sync each folder
            for folder in folders:
                if folder in self.config.get("EXCLUDE_FOLDERS", []):
                    logger.info(f"Skipping excluded folder: {folder}")
                    continue

                self._sync_folder(folder)

            # Close connection
            self.email_provider.close()

            logger.info("Email synchronization completed")
            return True
        except Exception as e:
            logger.exception(f"Error during email synchronization: {e!s}")
            return False

    def _sync_folder(self, folder) -> None:
        """Synchronize emails from a specific folder.

        Args:
        ----
            folder: Folder name to synchronize

        """
        logger.info(f"Synchronizing folder: {folder}")

        try:
            # Get list of emails in the folder
            email_ids = self.email_provider.get_emails(folder)
            logger.info(f"Found {len(email_ids)} emails in folder {folder}")

            # Process each email
            processed_count = 0
            skipped_count = 0

            for email_id in email_ids:
                # Check if email already exists in database (by UID)
                uid, raw_email = self.email_provider.get_email_content(email_id, folder)

                if not uid or not raw_email:
                    logger.warning(
                        f"Failed to fetch email {email_id} in folder {folder}",
                    )
                    continue

                # Check if email already exists
                if self._email_exists(uid):
                    skipped_count += 1
                    continue

                # Process the email
                if self._process_email(uid, raw_email, folder):
                    processed_count += 1

                # Add a small delay to avoid overwhelming the server
                time.sleep(0.1)

            logger.info(
                f"Folder {folder}: {processed_count} emails processed, {skipped_count} emails skipped",
            )
        except Exception as e:
            logger.exception(f"Error synchronizing folder {folder}: {e!s}")

    def _email_exists(self, uid):
        """Check if an email with the given UID already exists in the database.

        Args:
        ----
            uid: Email UID to check

        Returns:
        -------
            bool: True if email exists, False otherwise

        """
        conn = sqlite3.connect(self.emails_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM emails WHERE uid = ?", (uid,))
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def _process_email(self, uid, raw_email, folder) -> bool | None:
        """Process an email and store it in the database.

        Args:
        ----
            uid: Email UID
            raw_email: Raw email content
            folder: Folder name

        Returns:
        -------
            bool: True if successful, False otherwise

        """
        try:
            # Parse the email
            subject, sender, recipient, cc, body, raw_body, date = self._parse_email(
                raw_email,
            )

            # Store the email in the database
            conn = sqlite3.connect(self.emails_db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO emails (uid, sender, recipient, cc, subject, body, raw_body, folder, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (uid, sender, recipient, cc, subject, body, raw_body, folder, date),
            )

            conn.commit()
            email_id = cursor.lastrowid
            conn.close()

            logger.debug(f"Stored email with UID {uid}, ID {email_id}")

            # Process metadata if enabled
            if self.config.get("ENABLE_METADATA", True) and METADATA_ENABLED:
                self._process_email_metadata(
                    email_id,
                    sender,
                    recipient,
                    cc,
                    subject,
                    body,
                    raw_body,
                    date,
                )

            return True
        except Exception as e:
            logger.exception(f"Error processing email with UID {uid}: {e!s}")
            return False

    def _parse_email(self, raw_email):
        """Parse the raw email content and extract all email data.

        Args:
        ----
            raw_email: Raw email content

        Returns:
        -------
            tuple: (subject, sender, recipient, cc, body, raw_body, date)

        """
        try:
            import mailparser

            parsed_mail = mailparser.parse_from_bytes(raw_email)

            # Extract and clean basic fields
            subject = (parsed_mail.subject or "").strip()
            sender = parsed_mail.from_[0][1] if parsed_mail.from_ else ""
            recipient = parsed_mail.to[0][1] if parsed_mail.to else ""
            cc_list = [cc[1] for cc in (parsed_mail.cc or [])]
            cc = "; ".join(cc_list)
            date = parsed_mail.date.isoformat() if parsed_mail.date else ""

            # Store raw message body
            raw_body = raw_email.decode("utf-8", errors="replace")

            # Handle different content types
            body = ""
            if parsed_mail.text_plain:
                body = parsed_mail.text_plain[0]
            elif parsed_mail.text_html:
                body = parsed_mail.text_html[0]
            elif hasattr(parsed_mail, "calendar") and parsed_mail.calendar:
                # Try to find calendar content in attachments
                for attachment in parsed_mail.attachments:
                    if attachment.get("content_type", "").startswith("text/calendar"):
                        calendar_data = attachment.get("payload", "")
                        body = self._parse_calendar_content(calendar_data)
                        break
                if not body:  # If no calendar attachment found
                    body = "[Calendar Invite - No Details Available]"

                logger.info("Calendar content found and marked")
            else:
                body = parsed_mail.body or ""

        except Exception as e:
            logger.exception(
                f"Error parsing email with mailparser: {e!s}. Falling back to standard parsing.",
            )
            return self._parse_email_fallback(raw_email)

        # Validate and clean email addresses
        sender = self._validate_email_address(sender)
        recipient = self._validate_email_address(recipient)
        cc = "; ".join(
            [self._validate_email_address(cc_addr) for cc_addr in cc_list if cc_addr],
        )

        return subject, sender, recipient, cc, body, raw_body, date

    def _parse_email_fallback(self, raw_email):
        """Fallback parsing using Python's standard library.

        Args:
        ----
            raw_email: Raw email content

        Returns:
        -------
            tuple: (subject, sender, recipient, cc, body, raw_body, date)

        """
        try:
            msg = email.message_from_bytes(raw_email)
            subject = msg.get("subject", "")
            parts = decode_header(subject)
            decoded_subject = "".join(
                [
                    (
                        part.decode(encoding if encoding else "utf-8")
                        if isinstance(part, bytes)
                        else part
                    )
                    for part, encoding in parts
                ],
            )
            sender = msg.get("from", "")
            recipient = msg.get("to", "")
            cc = msg.get("cc", "")
            date = msg.get("date", "")

            # Store raw message body
            raw_body = raw_email.decode("utf-8", errors="replace")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if (
                        part.get_content_type() == "text/plain"
                        and "attachment" not in str(part.get("Content-Disposition", ""))
                    ):
                        try:
                            body = part.get_payload(decode=True).decode(
                                "utf-8",
                                errors="replace",
                            )
                            break
                        except Exception as e:
                            logger.exception(f"Error decoding email part: {e!s}")
            else:
                try:
                    body = msg.get_payload(decode=True).decode(
                        "utf-8",
                        errors="replace",
                    )
                except Exception as e:
                    logger.exception(f"Error decoding email: {e!s}")

            return decoded_subject, sender, recipient, cc, body, raw_body, date
        except Exception as e:
            logger.exception(f"Error in fallback email parsing: {e!s}")
            return "", "", "", "", "", raw_email.decode("utf-8", errors="replace"), ""

    def _parse_calendar_content(self, calendar_data):
        """Parse calendar content and return a formatted string.

        Args:
        ----
            calendar_data: Calendar data in iCalendar format

        Returns:
        -------
            str: Formatted calendar event details

        """
        try:
            if isinstance(calendar_data, str):
                calendar_data = calendar_data.encode("utf-8")

            cal = icalendar.Calendar.from_ical(calendar_data)
            event_details = []

            for component in cal.walk():
                if component.name == "VEVENT":
                    # Handle date objects vs datetime objects
                    start = component.get("dtstart", "No Start Date").dt
                    end = component.get("dtend", "No End Date").dt
                    if isinstance(start, datetime.date) and not isinstance(
                        start,
                        datetime.datetime,
                    ):
                        start = datetime.datetime.combine(start, datetime.time.min)
                    if isinstance(end, datetime.date) and not isinstance(
                        end,
                        datetime.datetime,
                    ):
                        end = datetime.datetime.combine(end, datetime.time.max)

                    event = {
                        "summary": str(component.get("summary", "No Title")),
                        "start": start,
                        "end": end,
                        "location": str(component.get("location", "No Location")),
                        "description": str(
                            component.get("description", "No Description"),
                        ),
                        "organizer": str(component.get("organizer", "No Organizer")),
                        "status": str(component.get("status", "No Status")),
                        "attendees": [str(a) for a in component.get("attendee", [])],
                    }
                    event_details.append(
                        f"Event: {event['summary']}\n"
                        f"When: {event['start'].strftime('%Y-%m-%d %H:%M')} - {event['end'].strftime('%Y-%m-%d %H:%M')}\n"
                        f"Where: {event['location']}\n"
                        f"Organizer: {event['organizer']}\n"
                        f"Status: {event['status']}\n"
                        f"Attendees: {', '.join(event['attendees']) if event['attendees'] else 'None'}\n"
                        f"Description: {event['description']}\n",
                    )

            return (
                "\n".join(event_details) if event_details else "[Empty Calendar Invite]"
            )
        except Exception as e:
            logger.debug(f"Error parsing calendar content: {e!s}", exc_info=True)
            return "[Calendar Parsing Failed]"

    def _validate_email_address(self, email_str):
        """Validates and normalizes an email address.

        Args:
        ----
            email_str: Email address to validate

        Returns:
        -------
            str: Validated email address or original string if invalid

        """
        if not email_str:
            return ""
        try:
            valid = validate_email(email_str, check_deliverability=False)
            return valid.normalized
        except EmailNotValidError:
            logger.debug(f"Invalid email address: {email_str}")
            return email_str  # Return original string instead of empty to preserve data

    def _process_email_metadata(
        self,
        email_id,
        sender,
        recipient,
        cc,
        subject,
        body,
        raw_body,
        date,
    ) -> bool | None:
        """Process metadata from an email.

        Args:
        ----
            email_id: Database ID of the email
            sender: Sender email address
            recipient: Recipient email address(es)
            cc: CC email address(es)
            subject: Email subject
            body: Email body
            raw_body: Raw email body
            date: Email date

        Returns:
        -------
            bool: True if successful, False otherwise

        """
        try:
            # Extract contacts if enabled
            if self.config.get("EXTRACT_CONTACTS", True) and self.contact_extractor:
                self.contact_extractor.extract_contacts_from_email(
                    email_id=email_id,
                    sender=sender,
                    recipients=recipient,
                    cc=cc,
                )
                logger.debug(f"Extracted contacts from email ID {email_id}")

            # Process calendar events if it's a calendar email
            if (
                self.config.get("EXTRACT_CALENDAR_EVENTS", True)
                and self.calendar_processor
            ):
                # Check if it's a calendar email
                if "[Calendar" in body:
                    # We may need to re-extract calendar data from raw_body
                    is_calendar = False

                    try:
                        import mailparser

                        parsed_mail = mailparser.parse_from_string(raw_body)

                        # Check for calendar attachments
                        for attachment in parsed_mail.attachments:
                            if attachment.get("content_type", "").startswith(
                                "text/calendar",
                            ):
                                calendar_data = attachment.get("payload", "")
                                self.calendar_processor.process_calendar_data(
                                    email_id,
                                    calendar_data,
                                )
                                is_calendar = True
                                break
                    except Exception as e:
                        logger.exception(
                            f"Error extracting calendar data from email ID {email_id}: {e!s}",
                        )

                    if is_calendar:
                        logger.info(f"Processed calendar data from email ID {email_id}")

            return True
        except Exception as e:
            logger.exception(
                f"Error processing metadata for email ID {email_id}: {e!s}",
            )
            return False

    def run(self) -> None:
        """Run the email sync service continuously."""
        logger.info("Starting email sync service")

        try:
            while True:
                # Sync emails
                self.sync_emails()

                # Wait for next sync
                sync_interval = self.config.get(
                    "SYNC_INTERVAL",
                    300,
                )  # Default: 5 minutes
                logger.info(f"Waiting {sync_interval} seconds for next sync")
                time.sleep(sync_interval)
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.exception(f"Service error: {e!s}")
        finally:
            # Ensure connections are closed
            if hasattr(self, "email_provider"):
                self.email_provider.close()

            logger.info("Email sync service stopped")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced Email Sync Service")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--metadata-db", help="Path to metadata database")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Create config from arguments
    config = {}
    if args.metadata_db:
        config["METADATA_DB_PATH"] = args.metadata_db

    # Initialize service
    service = EmailSyncService(config=args.config if args.config else config)

    # Run the service
    if args.once:
        service.sync_emails()
        logger.info("One-time sync completed")
    else:
        service.run()

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
