from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from dateutil import parser
from scripts.db_connector import DatabaseConnection, get_db_session
from scripts.gmail_client import GmailClient
from scripts.models import EmailProcessingHistory, RawEmail
from sqlalchemy.exc import SQLAlchemyError


def parse_email_date(date_str: str) -> datetime:
    """Parse email date string to datetime object.

    Handles various date formats from email headers.

    Args:
        date_str: Date string to parse from email headers.

    Returns:
        Parsed datetime object in UTC.

    Raises:
        ValueError: If date string cannot be parsed.
        TypeError: If input is not a string.

    """
    try:
        return parser.parse(date_str).astimezone(tz=None)
    except (ValueError, TypeError) as e:
        logging.exception(f"Failed to parse date '{date_str}': {e}")
        raise


def _extract_email_addresses(address_list: list) -> str:
    """Extract and format email addresses as a JSON string.

    Args:
        address_list: A list of email addresses.

    Returns:
        A JSON string representing the list of email addresses.

    """
    return json.dumps(address_list)


def _create_email_processing_history(
    email_id: uuid.UUID,
    now: datetime,
    session,
) -> None:
    """Create an EmailProcessingHistory record.

    Args:
        email_id: The UUID of the email being processed.
        now: The datetime when processing occurred.
        session: The database session.

    """
    processing_history = EmailProcessingHistory(
        id=uuid.uuid4(),
        email_id=email_id,
        version=1,
        processing_type="initial_fetch",
        status_from="none",
        status_to="new",
        changes={
            "action": "initial_fetch",
            "fields_processed": [
                "subject",
                "body",
                "headers",
                "labels",
                "from",
                "to",
                "cc",
                "bcc",
            ],
            "timestamp": now.isoformat(),
        },
        extra_data={
            "source": "gmail_api",
            "fetch_metadata": {
                "api_version": "v1",
                "fetch_timestamp": now.isoformat(),
                "processing_version": 1,
            },
        },
        created_by="system",
    )

    session.add(processing_history)
    session.commit()


def _create_raw_email(email: dict[str, Any], now: datetime) -> RawEmail:
    """Create a RawEmail instance from email data.

    Args:
        email: Dictionary containing raw email data from Gmail API.
        now: The datetime when processing occurred.

    Returns:
        A RawEmail instance.

    """
    from_str = email.get("from", "")
    from_name = from_str.split("<")[0].strip() if "<" in from_str else ""
    from_email = (
        from_str.split("<")[1].split(">")[0].strip() if "<" in from_str else from_str
    )
    to_addresses = _extract_email_addresses(email.get("to", []))
    cc_addresses = _extract_email_addresses(email.get("cc", []))
    bcc_addresses = _extract_email_addresses(email.get("bcc", []))
    labels = email.get("labels", [])
    label_names = email.get("label_names", [])
    extra_data = {
        "source": "gmail_api",
        "version": "1",
        "headers": email.get("headers", {}),
    }
    importance = 1 if "IMPORTANT" in labels else 0
    status = "new"

    return RawEmail(
        id=str(uuid.uuid4()),
        gmail_id=email["id"],
        thread_id=email["threadId"],
        subject=email.get("subject", ""),
        snippet=email.get("snippet", ""),
        plain_body=email.get("body_text", ""),
        html_body=email.get("body_html", ""),
        raw_content=email.get("raw", ""),
        from_name=from_name,
        from_email=from_email,
        to_addresses=to_addresses,
        cc_addresses=cc_addresses,
        bcc_addresses=bcc_addresses,
        received_date=parse_email_date(email["date"]),
        labels=labels,
        extra_data=extra_data,
        importance=importance,
        category=next((label for label in label_names if "CATEGORY_" in label), None),
        is_draft="DRAFT" in labels,
        is_sent="SENT" in labels,
        is_read="UNREAD" not in labels,
        is_starred="STARRED" in labels,
        is_trashed="TRASH" in labels,
        status=status,
        processing_version=1,
        processed_date=now,
        size_estimate=email.get("size_estimate", 0),
        created_by="system",
        updated_by="system",
    )


def process_email(email: dict[str, Any], session) -> None:
    """Process and store a single email in the database.

    Args:
        email: Dictionary containing raw email data from Gmail API.
        session: Active SQLAlchemy database session.

    Raises:
        SQLAlchemyError: If database operations fail.
        ValueError: If required email fields are missing.

    """
    try:
        now = datetime.now()
        raw_email = _create_raw_email(email, now)

        session.add(raw_email)
        session.commit()

        _create_email_processing_history(uuid.UUID(raw_email.id), now, session)

        logging.info(f"Successfully processed email {email['id']} with status new")

    except SQLAlchemyError as e:
        session.rollback()
        logging.exception(f"Database error while processing email {email['id']}: {e}")
        raise
    except Exception as e:
        logging.exception(f"Failed to process email {email['id']}: {e}")
        raise


class EmailProcessingError(Exception):
    """Base exception for email processing errors."""

    def __init__(
        self,
        message: str,
        email_id: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """Initialize EmailProcessingError.

        Args:
            message: Error description.
            email_id: ID of email being processed.
            original_exception: Original exception that caused the error.

        """
        self.timestamp = datetime.now()
        super().__init__(message)
        self.email_id = email_id
        self.original_exception = original_exception


class RateLimitError(EmailProcessingError):
    """Exception for rate limiting issues."""


class DatabaseError(EmailProcessingError):
    """Exception for database operations."""


class SchemaValidationError(EmailProcessingError):
    """Exception for schema validation failures."""


class ResourceError(EmailProcessingError):
    """Exception for resource-related issues."""


class EmailFetcher:
    """Main class for fetching and processing emails from Gmail."""

    def __init__(self, db_path: str, checkpoint_file: str) -> None:
        """Initialize EmailFetcher with database and checkpoint paths.

        Args:
            db_path: Path to SQLite database file.
            checkpoint_file: Path to JSON checkpoint file for tracking progress.

        Raises:
            ValueError: If paths are invalid.
            IOError: If files cannot be accessed.
            DatabaseError: If database connection fails.

        """
        self.logger = logging.getLogger(__name__)
        self.last_checkpoint: datetime | None = None
        self.db = DatabaseConnection(db_path=db_path)
        self.checkpoint_file = Path(checkpoint_file)
        self.gmail_client = GmailClient()

    def process_new_emails(self) -> None:
        """Process new emails from Gmail."""
        try:
            last_email_id = self.load_checkpoint()
            service = self.gmail_client.authenticate()
            emails = self._fetch_emails(service, last_email_id)

            with get_db_session() as session:
                for email in emails:
                    try:
                        process_email(email, session)
                    except Exception as e:
                        logging.exception(
                            f"Error processing email {email.get('id')}: {e}",
                        )
                        continue

        except Exception as e:
            logging.exception(f"Error in process_new_emails: {e}")
            raise

    def _fetch_emails(self, service: Any, last_email_id: str | None) -> list:
        """Fetch emails from Gmail API.

        Args:
            service: Authenticated Gmail API service.
            last_email_id: ID of the last processed email.

        Returns:
            A list of email dictionaries.

        """
        emails = []
        page_token = None
        while True:
            try:
                results = (
                    service.users()
                    .messages()
                    .list(userId="me", pageToken=page_token, maxResults=100)
                    .execute()
                )

                batch = results.get("messages", [])
                if not batch:
                    break

                if last_email_id:
                    for i, msg in enumerate(batch):
                        if msg["id"] == last_email_id:
                            batch = batch[:i]
                            break

                for msg_meta in batch:
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=msg_meta["id"], format="full")
                        .execute()
                    )
                    emails.append(msg)

                if batch:
                    self.save_checkpoint(batch[0]["id"])

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            except Exception as e:
                logging.exception(f"Error fetching emails: {e}")
                raise
        return emails

    def store_email(self, email_data: dict[str, Any]) -> None:
        """Store an email in the database.

        Args:
            email_data: Dictionary containing email data.

        Raises:
            DatabaseError: If database operations fail.
            ValueError: If required fields are missing.
            SchemaValidationError: If data doesn't match schema.

        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO emails (
                    id, thread_id, subject, snippet, body,
                    from_email, to_emails, cc_emails, bcc_emails,
                    labels, received_date, processed_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_data["id"],
                    email_data["threadId"],
                    email_data.get("subject", ""),
                    email_data.get("snippet", ""),
                    email_data.get("body", ""),
                    email_data.get("from", ""),
                    email_data.get("to", ""),
                    email_data.get("cc", ""),
                    email_data.get("bcc", ""),
                    json.dumps(email_data.get("labels", [])),
                    email_data["date"],
                    datetime.now().isoformat(),
                ),
            )

    def save_checkpoint(self, email_id: str) -> None:
        """Save the last processed email ID.

        Args:
            email_id: ID of the last processed email.

        Raises:
            IOError: If checkpoint file cannot be written.
            ValueError: If email_id is invalid.

        """
        self.last_checkpoint = datetime.now()
        with open(self.checkpoint_file, "w") as f:
            json.dump({"last_email_id": email_id}, f)

    def load_checkpoint(self) -> str | None:
        """Load the last processed email ID.

        Returns:
            The last processed email ID or None if no checkpoint exists.

        Raises:
            IOError: If checkpoint file cannot be read.
            ValueError: If checkpoint data is invalid.

        """
        try:
            with open(self.checkpoint_file) as f:
                data = json.load(f)
                return data.get("last_email_id")
        except (FileNotFoundError, json.JSONDecodeError):
            return None
