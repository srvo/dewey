"""Unified Email Client Module

This module provides a unified interface for interacting with email accounts,
supporting both Gmail-specific APIs and generic IMAP protocols.
"""

import email
import email.policy
import imaplib
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from typing import Any, Dict, List, Optional, Tuple

from dewey.core.base_script import BaseScript


class EmailClient(BaseScript):
    """A unified client for interacting with email accounts.

    This class provides a consistent interface for email operations,
    supporting both Gmail-specific APIs and standard IMAP protocols.
    """

    def __init__(self, provider: str = "gmail") -> None:
        """Initialize the EmailClient.

        Args:
            provider: The email provider ('gmail' or 'generic_imap')

        """
        super().__init__(config_section="email_client", requires_db=True)
        self.provider = provider
        self.imap_conn = None
        self.gmail_service = None

        if provider == "gmail":
            self._setup_gmail()
        else:
            self._setup_imap()

    def _setup_gmail(self) -> None:
        """Set up Gmail-specific API connection."""
        try:
            # This will be implemented when we integrate the Gmail API code
            self.logger.info("Setting up Gmail API connection")
            # For now, we'll use IMAP for Gmail as well
            self._setup_imap()
        except Exception as e:
            self.logger.error(f"Failed to set up Gmail API: {e}")
            raise

    def _setup_imap(self) -> None:
        """Set up IMAP connection."""
        try:
            self.logger.info("Setting up IMAP connection")

            # Get connection details from config or environment variables
            imap_server = self.get_config_value(
                "imap_server", os.environ.get("IMAP_SERVER", "imap.gmail.com")
            )
            imap_port = int(
                self.get_config_value("imap_port", os.environ.get("IMAP_PORT", "993"))
            )

            # First try to get from config, then from environment variables
            username = self.get_config_value("email_username", None)
            if not username:
                username = os.environ.get("EMAIL_USERNAME")

            password = self.get_config_value("email_password", None)
            if not password:
                password = os.environ.get("EMAIL_PASSWORD")

            if not username or not password:
                raise ValueError(
                    "Missing email credentials in configuration or environment variables"
                )

            # Connect to the IMAP server
            self.imap_conn = imaplib.IMAP4_SSL(imap_server, imap_port)
            self.imap_conn.login(username, password)
            self.logger.info(f"Successfully connected to IMAP server: {imap_server}")

        except Exception as e:
            self.logger.error(f"Failed to set up IMAP connection: {e}")
            raise

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 100,
        since_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch emails from the specified folder.

        Args:
            folder: The email folder to fetch from
            limit: Maximum number of emails to fetch
            since_date: Only fetch emails since this date

        Returns:
            A list of dictionaries containing email data

        """
        if self.provider == "gmail" and self.gmail_service:
            return self._fetch_emails_gmail(folder, limit, since_date)
        elif self.imap_conn:
            return self._fetch_emails_imap(folder, limit, since_date)
        else:
            raise RuntimeError("No email connection available")

    def _fetch_emails_gmail(
        self,
        folder: str = "INBOX",
        limit: int = 100,
        since_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch emails using Gmail API.

        Args:
            folder: The email folder/label to fetch from
            limit: Maximum number of emails to fetch
            since_date: Only fetch emails since this date

        Returns:
            A list of dictionaries containing email data

        """
        # This will be implemented when we integrate the Gmail API
        # For now, we'll use IMAP
        return self._fetch_emails_imap(folder, limit, since_date)

    def _fetch_emails_imap(
        self,
        folder: str = "INBOX",
        limit: int = 100,
        since_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch emails using IMAP protocol.

        Args:
            folder: The email folder to fetch from
            limit: Maximum number of emails to fetch
            since_date: Only fetch emails since this date

        Returns:
            A list of dictionaries containing email data

        """
        try:
            if not self.imap_conn:
                raise RuntimeError("No IMAP connection available")

            # Select the folder
            self.imap_conn.select(folder)

            # Build search criteria
            search_criteria = "ALL"
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                search_criteria = f'(SINCE "{date_str}")'

            # Search for emails
            status, data = self.imap_conn.search(None, search_criteria)
            if status != "OK":
                raise RuntimeError(f"Failed to search emails: {status}")

            # Get email IDs and limit them
            email_ids = data[0].split()
            if limit and len(email_ids) > limit:
                email_ids = email_ids[-limit:]

            # Fetch and process emails
            emails = []
            for email_id in email_ids:
                status, data = self.imap_conn.fetch(email_id, "(RFC822)")
                if status != "OK":
                    self.logger.warning(f"Failed to fetch email {email_id}: {status}")
                    continue

                raw_email = data[0][1]
                email_message = email.message_from_bytes(
                    raw_email, policy=email.policy.default
                )

                # Process email
                email_data = self._process_email_message(email_message, email_id)
                emails.append(email_data)

            return emails

        except Exception as e:
            self.logger.error(f"Error fetching emails via IMAP: {e}")
            raise

    def _process_email_message(
        self, email_message: Message, email_id: bytes
    ) -> dict[str, Any]:
        """Process an email message into a structured dictionary.

        Args:
            email_message: The email message object
            email_id: The email ID

        Returns:
            A dictionary containing processed email data

        """
        # Extract basic headers
        subject = self._decode_header(email_message.get("Subject", ""))
        from_header = self._decode_header(email_message.get("From", ""))
        to_header = self._decode_header(email_message.get("To", ""))
        date_str = email_message.get("Date", "")

        # Parse the from header to extract email and name
        from_name, from_email = self._parse_email_header(from_header)

        # Extract email date
        try:
            email_date = email.utils.parsedate_to_datetime(date_str)
        except:
            email_date = datetime.now()

        # Get email body
        body_text, body_html = self._get_email_body(email_message)

        # Build the email data dictionary
        email_data = {
            "email_id": email_id.decode(),
            "subject": subject,
            "from_name": from_name,
            "from_email": from_email,
            "to": to_header,
            "date": email_date,
            "body_text": body_text,
            "body_html": body_html,
            "has_attachments": bool(list(email_message.iter_attachments())),
        }

        return email_data

    def _decode_header(self, header: str) -> str:
        """Decode an email header string.

        Args:
            header: The header string to decode

        Returns:
            The decoded header string

        """
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    if encoding:
                        decoded_parts.append(part.decode(encoding))
                    else:
                        decoded_parts.append(part.decode())
                except:
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(part)
        return " ".join(decoded_parts)

    def _parse_email_header(self, header: str) -> tuple[str, str]:
        """Parse an email header to extract name and email address.

        Args:
            header: The header string to parse

        Returns:
            A tuple containing (name, email_address)

        """
        name = ""
        email_address = ""

        # Use regex to extract email
        email_match = re.search(r"<(.+?)>|(\S+@\S+)", header)
        if email_match:
            email_address = email_match.group(1) or email_match.group(2)

            # Extract name (everything before the email)
            if "<" in header:
                name = header.split("<")[0].strip()
                # Remove quotes if present
                if name.startswith('"') and name.endswith('"'):
                    name = name[1:-1]
        else:
            email_address = header

        return name, email_address

    def _get_email_body(self, email_message: Message) -> tuple[str, str]:
        """Extract text and HTML body from an email message.

        Args:
            email_message: The email message object

        Returns:
            A tuple containing (text_body, html_body)

        """
        text_body = ""
        html_body = ""

        if email_message.is_multipart():
            for part in email_message.get_payload():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                try:
                    body = part.get_payload(decode=True)
                    if body:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            decoded_body = body.decode(charset)
                        except:
                            decoded_body = body.decode("utf-8", errors="replace")

                        if content_type == "text/plain":
                            text_body = decoded_body
                        elif content_type == "text/html":
                            html_body = decoded_body
                except:
                    self.logger.warning("Failed to decode email part")
        else:
            # Not multipart - just get the body
            content_type = email_message.get_content_type()
            try:
                body = email_message.get_payload(decode=True)
                if body:
                    charset = email_message.get_content_charset() or "utf-8"
                    try:
                        decoded_body = body.decode(charset)
                    except:
                        decoded_body = body.decode("utf-8", errors="replace")

                    if content_type == "text/plain":
                        text_body = decoded_body
                    elif content_type == "text/html":
                        html_body = decoded_body
            except:
                self.logger.warning("Failed to decode email body")

        return text_body, html_body

    def save_emails_to_db(self, emails: list[dict[str, Any]]) -> None:
        """Save fetched emails to the database.

        Args:
            emails: A list of email dictionaries to save

        Returns:
            None

        """
        try:
            if not self.db_conn:
                raise RuntimeError("No database connection available")

            # Create the emails table if it doesn't exist
            self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS crm_emails (
                email_id VARCHAR PRIMARY KEY,
                subject VARCHAR,
                from_name VARCHAR,
                from_email VARCHAR,
                to_field VARCHAR,
                date TIMESTAMP,
                body_text TEXT,
                body_html TEXT,
                has_attachments BOOLEAN,
                processed BOOLEAN DEFAULT FALSE,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Insert emails into the database
            for email_data in emails:
                self.db_conn.execute(
                    """
                INSERT OR IGNORE INTO crm_emails
                (email_id, subject, from_name, from_email, to_field, date, body_text, body_html, has_attachments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        email_data["email_id"],
                        email_data["subject"],
                        email_data["from_name"],
                        email_data["from_email"],
                        email_data["to"],
                        email_data["date"],
                        email_data["body_text"],
                        email_data["body_html"],
                        email_data["has_attachments"],
                    ),
                )

            self.db_conn.commit()
            self.logger.info(f"Saved {len(emails)} emails to database")

        except Exception as e:
            self.logger.error(f"Error saving emails to database: {e}")
            raise

    def close(self) -> None:
        """Close all connections."""
        if self.imap_conn:
            try:
                self.imap_conn.close()
                self.imap_conn.logout()
            except:
                pass
            finally:
                self.imap_conn = None

        self.gmail_service = None

    def run(self) -> None:
        """Run the email import process.

        This method orchestrates the email import process by:
        1. Connecting to the email account
        2. Fetching emails
        3. Saving them to the database
        4. Closing connections
        """
        self.logger.info("Starting email import process")

        try:
            # Get import parameters from config
            folder = self.get_config_value("email_folder", "INBOX")
            limit = int(self.get_config_value("email_limit", "100"))
            days_back = int(self.get_config_value("days_back", "30"))
            since_date = datetime.now() - timedelta(days=days_back)

            # Fetch emails
            self.logger.info(
                f"Fetching emails from {folder} (limit: {limit}, since: {since_date})"
            )
            emails = self.fetch_emails(folder, limit, since_date)
            self.logger.info(f"Fetched {len(emails)} emails")

            # Save to database
            if emails:
                self.save_emails_to_db(emails)

            self.logger.info("Email import completed successfully")

        except Exception as e:
            self.logger.error(f"Error during email import: {e}")
            raise
        finally:
            # Ensure connections are closed
            self.close()


if __name__ == "__main__":
    client = EmailClient()
    client.run()
