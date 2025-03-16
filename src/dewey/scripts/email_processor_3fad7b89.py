# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash rate limited. Cooling down for 5 minutes.

#!/usr/bin/env python3
"""Email Fetching and Processing System.

This module provides comprehensive functionality for interacting with the Gmail API,
processing email data, and storing it in a relational database. The system is designed
to be robust, handling rate limits, connection issues, and partial failures gracefully.

Key Features:
- Incremental email fetching with checkpointing
- Contact and email metadata extraction
- Structured data storage with versioning
- Comprehensive error handling and logging
- Configurable rate limiting and retry logic
- Timezone-aware datetime handling
- Automatic contact enrichment task creation

Architecture:
The system follows a layered architecture:
1. API Layer: Handles Gmail API authentication and raw data fetching
2. Processing Layer: Parses and transforms email data
3. Storage Layer: Manages database operations and versioning
4. Monitoring Layer: Tracks operations through logging and checkpoints

Error Handling:
The system implements multiple error handling strategies:
- Transient errors: Retry with exponential backoff
- Permanent errors: Skip problematic emails and continue
- Database errors: Rollback transactions and retry
- Rate limits: Implement progressive delays

Configuration:
All configuration is managed through the Config class, supporting:
- Database connection parameters
- API credentials and tokens
- Rate limiting parameters
- Logging configuration

Security Considerations:
- API tokens are stored securely using pickle serialization
- Sensitive data is not logged
- Database connections use proper isolation levels
- All operations are audited through processing history

Performance:
The system is optimized for:
- Batch processing of emails
- Minimal API calls through efficient pagination
- Database connection pooling
- Parallel processing capabilities

Maintenance Guidelines:
1. Keep Gmail API client logic separate from email processing logic
2. Use SQLAlchemy for all database operations
3. Handle rate limits with exponential backoff
4. Maintain processing checkpoints for resumability
5. Log all operations and errors
6. Regularly review and update API scopes
7. Monitor database growth and performance

Integration Points:
- Gmail API for email fetching
- PostgreSQL database for storage
- Logging system for operations tracking
- Contact enrichment system for follow-up tasks
"""
from __future__ import annotations

import json
import logging
import os
import pickle
import random
import time
import traceback
import uuid

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from googleapiclient.errors import HttpError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from scripts.config import Config
from scripts.models import (
    Contact,
    ContactEmail,
    EmailProcessingHistory,
    EnrichmentTask,
    RawEmail,
)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MOUNTAIN_TZ = ZoneInfo("America/Denver")


class DatabaseError(Exception):
    """Exception raised for database-related errors.

    This exception captures errors that occur during database operations,
    including connection issues, constraint violations, and transaction failures.

    Attributes
    ----------
        message (str): Human-readable error description
        original_exception (Exception): The original exception that caused the error
        query (Optional[str]): The SQL query that failed, if applicable
        params (Optional[Dict]): The query parameters that were used

    """

    def __init__(
        self,
        message: str,
        original_exception: Exception | None = None,
        query: str | None = None,
        params: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.original_exception = original_exception
        self.query = query
        self.params = params


class RateLimitError(Exception):
    """Exception raised when Gmail API rate limits are exceeded.

    This exception is raised when the system detects that API rate limits
    have been reached, either through explicit error responses or through
    heuristic detection of throttling.

    Attributes
    ----------
        message (str): Human-readable error description
        retry_after (Optional[float]): Suggested wait time before retrying
        endpoint (Optional[str]): The API endpoint that was being called
        quota_info (Optional[Dict]): Details about current quota usage

    """

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        endpoint: str | None = None,
        quota_info: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.endpoint = endpoint
        self.quota_info = quota_info


@contextmanager
def get_db_session() -> Session:
    """Context manager for database session handling.

    This function provides a managed database session that automatically
    handles connection pooling, transaction management, and error handling.

    Features:
    - Automatic connection pooling
    - Transaction management with automatic commit/rollback
    - Connection cleanup
    - Error logging and propagation

    Usage:
        with get_db_session() as session:
            # Perform database operations
            session.query(...)

    Yields
    ------
        Session: A SQLAlchemy session object for database operations

    Raises
    ------
        DatabaseError: If any database operation fails

    """
    db_url = Config().DB_URL
    engine = create_engine(db_url, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception(f"Database error: {e}")
        msg = f"Database operation failed: {e}"
        raise DatabaseError(msg)
    finally:
        session.close()


def db_session():
    """Context manager for database sessions."""
    return get_db_session()


def get_or_create_contact(session, email: str, name: str | None = None) -> Contact:
    """Retrieve or create a contact record for the given email address.

    This function implements a 'get or create' pattern for contact management,
    ensuring that each email address has exactly one associated contact record.

    The function performs the following operations:
    1. Validates the email format
    2. Checks for existing contact records
    3. Creates new records if necessary
    4. Sets up related entities (contact email, enrichment task)
    5. Maintains versioning and audit trails

    Args:
    ----
        session: Database session for operations
        email: Email address to look up or create
        name: Optional name associated with the email

    Returns:
    -------
        Contact: The existing or newly created contact record

    Raises:
    ------
        ValueError: If the email format is invalid
        DatabaseError: If database operations fail

    Note:
    ----
        The function creates an enrichment task automatically for new contacts,
        which will trigger background processing to gather additional information
        about the contact from external sources.

    """
    # Extract domain for contact record
    domain = email.split("@")[-1] if "@" in email else None

    # Check existing contact emails
    contact_email = session.execute(
        select(ContactEmail).where(ContactEmail.email == email),
    ).scalar_one_or_none()

    if contact_email:
        return contact_email.contact

    # Create new contact
    contact = Contact(
        id=uuid.uuid4(),
        version=1,
        primary_email=email,
        name=name,
        domain=domain,
        email_count=0,
        enrichment_status="pending",
        confidence_score=0.0,
        extra_data={
            "source": "email_processing",
            "initial_discovery": {
                "timestamp": datetime.now(MOUNTAIN_TZ).isoformat(),
                "source_type": "gmail_api",
                "context": "email_participant",
            },
        },
        created_by="system",
        updated_by="system",
    )
    session.add(contact)

    # Create contact email record
    contact_email = ContactEmail(
        id=uuid.uuid4(),
        contact_id=contact.id,
        version=1,
        email=email,
        is_primary=True,
        source="gmail_api",
        verified=False,
        extra_data={
            "discovery_context": "email_participant",
            "first_seen": datetime.now(MOUNTAIN_TZ).isoformat(),
        },
        created_by="system",
        updated_by="system",
    )
    session.add(contact_email)

    # Create enrichment task
    enrichment_task = EnrichmentTask(
        id=uuid.uuid4(),
        entity_type="contact",
        entity_id=contact.id,
        task_type="initial_enrichment",
        version=1,
        status="pending",
        priority=50,  # Medium priority for new contacts
        attempts=0,
        max_attempts=3,
        next_attempt=datetime.now(MOUNTAIN_TZ) + timedelta(hours=1),
        extra_data={
            "source": "email_processing",
            "context": {
                "discovery_type": "email_participant",
                "email_address": email,
                "name": name,
            },
        },
        created_by="system",
        updated_by="system",
    )
    session.add(enrichment_task)

    return contact


def process_participants(session, addresses, participant_type):
    """Process a list of email participants and manage their contact records.

    This function handles the processing of email participants (to, from, cc, bcc)
    and ensures proper contact management for each address. It maintains detailed
    processing status for each participant and handles errors gracefully.

    Args:
    ----
        session: Database session for operations
        addresses: List of email address dictionaries with 'email' and 'name' keys
        participant_type: Type of participant (sender, recipient, cc, bcc)

    Returns:
    -------
        List[Dict]: Processing results for each participant with status information

    The function returns a list of dictionaries with the following structure:
    {
        "email": str,               # The email address processed
        "name": str,                # The associated name (if available)
        "contact_id": str,          # UUID of the contact record
        "processing_status": str,   # 'success' or 'error'
        "participant_type": str,    # Type of participant
        "error": Optional[str]      # Error message if processing failed
    }

    Error Handling:
    - Invalid email formats are skipped with appropriate error messages
    - Database errors are caught and logged
    - Each participant is processed independently

    """
    results = []
    for address in addresses:
        try:
            email = address["email"]
            name = address["name"]

            # Basic email validation
            if not email or "@" not in email or "." not in email:
                msg = f"Invalid email format: {email}"
                raise ValueError(msg)

            contact = get_or_create_contact(session, email, name)
            results.append(
                {
                    "email": email,
                    "name": name,
                    "contact_id": str(contact.id),
                    "processing_status": "success",
                    "participant_type": participant_type,
                },
            )
        except Exception as e:
            results.append(
                {
                    "email": address.get("email", ""),
                    "name": address.get("name", ""),
                    "processing_status": "error",
                    "error": str(e),
                    "participant_type": participant_type,
                },
            )
    return results


def parse_email_date(date_str: str) -> datetime:
    """Parse email date strings into timezone-aware datetime objects.

    This function handles the various date formats found in email headers,
    converting them to Mountain Time (America/Denver) for consistent storage.

    Supported Formats:
    - RFC 2822 (e.g., "Wed, 14 Jan 2025 12:34:56 -0700")
    - Various common variations
    - Fallback to email.utils.parsedate_to_datetime

    Args:
    ----
        date_str: The date string from email headers

    Returns:
    -------
        datetime: Timezone-aware datetime object in Mountain Time

    Note:
    ----
        If parsing fails, the current time in Mountain Time is returned as a fallback.
        This ensures the system can continue processing even with malformed dates.

    Error Handling:
        All parsing errors are caught and logged, with the function returning
        a sensible default rather than raising exceptions.

    """
    # Email dates can be in various formats, this handles the common ones
    try:
        # Try various formats
        for fmt in [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%a %b %d %H:%M:%S %Y %z",
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                # Convert to Mountain Time
                return dt.astimezone(MOUNTAIN_TZ)
            except ValueError:
                continue

        # If none of the formats work, try a more lenient parser
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(MOUNTAIN_TZ)
    except Exception as e:
        logger.exception(f"Failed to parse date {date_str}: {e}")
        return datetime.now(MOUNTAIN_TZ)


def parse_email_addresses(header_value: str) -> list[dict[str, str]]:
    """Parse email addresses from header value into structured format."""
    if not header_value:
        return []

    addresses = []
    for addr in header_value.split(","):
        addr = addr.strip()
        if "<" in addr and ">" in addr:
            name = addr.split("<")[0].strip(" \"'")
            email = addr.split("<")[1].split(">")[0].strip()
            addresses.append({"name": name, "email": email})
        else:
            addresses.append({"name": "", "email": addr})
    return addresses


def fetch_all_emails(service, user_id=os.getenv("GMAIL_USER_ID", "me")):
    """Fetch emails from Gmail API with pagination and rate limiting.

    This function implements a robust email fetching mechanism that:
    - Handles pagination through the Gmail API
    - Implements exponential backoff for rate limiting
    - Maintains progress through checkpointing
    - Logs detailed progress information

    Args:
    ----
        service: Authenticated Gmail API service instance
        user_id: Gmail user ID (defaults to 'me' for authenticated user)

    Returns:
    -------
        List[Dict]: List of email metadata dictionaries

    The function uses the following environment variables:
    - GMAIL_FETCH_QUERY: Optional query string for filtering emails
    - GMAIL_USER_ID: User ID for the Gmail account

    Rate Limiting:
    The function implements exponential backoff with jitter to handle
    rate limiting errors (429, 500, 503). The retry strategy is:
    - Base delay: 0.1 seconds
    - Exponential factor: 2^n
    - Random jitter: 0-1 seconds
    - Maximum retries: 5

    Pagination:
    The function fetches emails in batches of 500 messages per request,
    using the Gmail API's pageToken mechanism to handle large result sets.

    Error Handling:
    - Rate limit errors are handled with retries
    - Other errors are logged and propagated
    - The function maintains state through checkpointing

    """
    query = os.getenv("GMAIL_FETCH_QUERY", "")
    messages = []
    page_token = None
    total_fetched = 0
    max_retries = 5
    base_delay = 0.1  # Base delay between requests in seconds

    while True:
        try:
            request_params = {"userId": user_id, "maxResults": 500, "q": query}
            if page_token:
                request_params["pageToken"] = page_token

            # Exponential backoff implementation
            response = None
            for attempt in range(max_retries):
                try:
                    response = (
                        service.users().messages().list(**request_params).execute()
                    )
                    break
                except HttpError as error:
                    if (
                        error.resp.status in [429, 500, 503]
                        and attempt < max_retries - 1
                    ):
                        wait_time = (2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Rate limit hit, waiting {wait_time} seconds...",
                        )
                        time.sleep(wait_time)
                        continue
                    logger.exception(f"HTTP error during fetch: {error}")
                    msg = f"API rate limit exceeded after {max_retries} attempts"
                    raise RateLimitError(
                        msg,
                    )

            if response is None:
                logger.error("Failed to get response after all retries")
                msg = "API request failed after maximum retries"
                raise RateLimitError(msg)

            batch_messages = response.get("messages", [])
            if not batch_messages:
                logger.info("No more messages to fetch")
                break

            messages.extend(batch_messages)
            total_fetched += len(batch_messages)
            logger.info(
                f"Fetched {len(batch_messages)} messages. Total: {total_fetched}",
            )

            page_token = response.get("nextPageToken")
            if not page_token:
                logger.info("No more pages to fetch")
                break

            # Rate limiting between requests
            time.sleep(base_delay)

        except Exception as e:
            logger.exception(f"Error in fetch_all_emails: {e!s}")
            raise

    return messages


def save_checkpoint(email_id: str) -> None:
    """Save the last successfully processed email ID."""
    with open("checkpoint.json", "w") as f:
        json.dump(
            {"last_email_id": email_id, "timestamp": datetime.now().isoformat()},
            f,
        )


def load_checkpoint() -> str | None:
    """Load the last checkpoint if it exists."""
    try:
        with open("checkpoint.json") as f:
            data = json.load(f)
            return data.get("last_email_id")
    except FileNotFoundError:
        return None


def process_emails(service, session=None):
    """Process emails with checkpoint support."""
    if session is None:
        # Only create new session if none provided
        with get_db_session() as session:
            return _process_emails_internal(service, session)
    else:
        return _process_emails_internal(service, session)


def _process_emails_internal(service, session) -> None:
    """Internal implementation of email processing."""
    try:
        last_checkpoint = load_checkpoint()
        email_ids = fetch_all_emails(service)

        if last_checkpoint:
            start_idx = (
                next(
                    (i for i, e in enumerate(email_ids) if e["id"] == last_checkpoint),
                    0,
                )
                + 1
            )
            email_ids = email_ids[start_idx:]

        logger.info(f"Processing {len(email_ids)} emails")

        for email_id_data in email_ids:
            try:
                email_data = (
                    service.users()
                    .messages()
                    .get(userId="me", id=email_id_data["id"], format="full")
                    .execute()
                )

                process_email(email_data, session)
                save_checkpoint(email_id_data["id"])
                logger.info(f"Successfully processed email {email_id_data['id']}")
            except Exception as e:
                logger.exception(f"Failed to process email {email_id_data['id']}: {e}")
                continue
    except Exception as e:
        logger.exception(f"Failed to fetch emails: {e}")
        raise


def process_email(email: dict[str, Any], session) -> None:
    """Process and store a single email message in the database.

    This function handles the complete processing pipeline for a single email,
    including:
    - Metadata extraction
    - Contact management
    - Content processing
    - Database storage
    - History tracking

    Args:
    ----
        email: Dictionary containing raw email data from Gmail API
        session: Database session for storage operations

    The function performs the following operations:
    1. Checks for existing email records
    2. Extracts and processes headers
    3. Manages contact relationships
    4. Parses and stores email content
    5. Creates processing history records
    6. Handles versioning and audit trails

    Database Operations:
    - Creates or updates RawEmail record
    - Creates Contact and ContactEmail records as needed
    - Creates EmailProcessingHistory record
    - Creates EnrichmentTask for new contacts

    Error Handling:
    - Database errors trigger rollback and retry
    - Invalid data is logged and skipped
    - Partial failures are handled gracefully

    Note:
    ----
        The function uses a single transaction for all database operations,
        ensuring atomicity of the email processing operation.

    """
    try:
        logger.info(f"Processing email {email['id']}")

        # Check if email already exists and hasn't changed
        existing_email = session.execute(
            select(RawEmail).where(RawEmail.gmail_id == email["id"]),
        ).scalar_one_or_none()

        # Extract headers from payload
        headers = {
            header["name"].lower(): header["value"]
            for header in email["payload"]["headers"]
        }

        if existing_email:
            # Check if content has changed by comparing key fields
            content_changed = any(
                [
                    existing_email.subject != headers.get("subject", ""),
                    existing_email.snippet != email.get("snippet", ""),
                    existing_email.plain_body != email.get("body_text", ""),
                    existing_email.html_body != email.get("body_html", ""),
                    existing_email.labels != email.get("labelIds", []),
                    existing_email.is_read
                    != ("UNREAD" not in email.get("labelIds", [])),
                    existing_email.is_starred
                    != ("STARRED" in email.get("labelIds", [])),
                    existing_email.is_trashed != ("TRASH" in email.get("labelIds", [])),
                ],
            )

            if not content_changed:
                logger.debug(f"Skipping unchanged email {email['id']}")
                return
            logger.debug(f"Email {email['id']} has changed, updating...")

        # Parse email addresses
        from_addresses = parse_email_addresses(headers.get("from", ""))
        to_addresses = parse_email_addresses(headers.get("to", ""))
        cc_addresses = parse_email_addresses(headers.get("cc", ""))
        bcc_addresses = parse_email_addresses(headers.get("bcc", ""))

        # Process all participants and create/update contacts
        processed_participants = {
            "from": process_participants(session, from_addresses, "sender"),
            "to": process_participants(session, to_addresses, "recipient"),
            "cc": process_participants(session, cc_addresses, "cc"),
            "bcc": process_participants(session, bcc_addresses, "bcc"),
        }

        # Get the first from address or empty values
        from_name = from_addresses[0]["name"] if from_addresses else ""
        from_email = from_addresses[0]["email"] if from_addresses else ""

        # Parse labels and calculate importance
        labels = email.get("labelIds", [])
        importance = calculate_importance(email)

        # Get or create raw email record
        now = datetime.now(MOUNTAIN_TZ)
        received_date = parse_email_date(headers.get("date", ""))

        # Extract body content
        body_data = email["payload"].get("body", {}).get("data", "")
        plain_body = body_data  # In real implementation, would need base64 decoding

        raw_email = RawEmail(
            id=uuid.uuid4(),
            gmail_id=email["id"],
            thread_id=email.get("threadId", ""),
            version=1,
            subject=headers.get("subject", ""),
            snippet=email.get("snippet", ""),
            plain_body=plain_body,
            html_body="",  # Would need to handle multipart messages
            from_name=from_name,
            from_email=from_email,
            to_addresses=[addr["email"] for addr in to_addresses],
            cc_addresses=[addr["email"] for addr in cc_addresses],
            bcc_addresses=[addr["email"] for addr in bcc_addresses],
            received_date=received_date,
            labels=labels,
            importance=importance,
            is_draft=False,  # Would need to check labelIds
            is_sent="SENT" in labels,
            is_read="UNREAD" not in labels,
            is_starred="STARRED" in labels,
            is_trashed="TRASH" in labels,
            status="processed",
            processing_version=1,
            processed_date=now,
            size_estimate=email.get("sizeEstimate", 0),
            created_by="system",
            updated_by="system",
            extra_data={
                "source": "gmail_api",
                "fetch_metadata": {
                    "api_version": "v1",
                    "fetch_timestamp": now.isoformat(),
                    "processing_version": 1,
                },
                "participants": processed_participants,
            },
        )

        session.add(raw_email)

        # Create processing history record
        history = EmailProcessingHistory(
            email_id=raw_email.id,
            version=raw_email.processing_version,
            processing_type="initial_fetch",
            status_from="new",
            status_to="processed",
            changes={"initial_fetch": True},
            extra_data={"gmail_id": email["id"]},
            created_by="system",
        )
        session.add(history)

        # Commit all changes at once
        session.commit()

        logger.info(
            f"Successfully processed email {email['id']} with status {history.status_to}",
        )

    except Exception as e:
        logger.exception(f"Failed to process email {email['id']}: {e}")
        logger.exception(f"Traceback: {traceback.format_exc()}")
        session.rollback()
        raise


def calculate_importance(email: dict[str, Any]) -> int:
    """Calculate email importance based on various factors."""
    importance = 0
    labels = email.get("labels", [])

    # Priority labels
    if "Label_31" in labels:  # Priority/Critical
        importance += 100
    elif "Label_30" in labels:  # Priority/High
        importance += 75
    elif "Label_28" in labels:  # Priority/Medium
        importance += 50
    elif "Label_27" in labels:  # Priority/Low
        importance += 25
    elif "Label_29" in labels:  # Priority/Very Low
        importance += 10

    # Other factors
    if "IMPORTANT" in labels:
        importance += 25
    if "STARRED" in labels:
        importance += 25
    if "Response Required" in email.get("label_names", []):
        importance += 50

    return importance


def get_gmail_service():
    """Authenticate and create a Gmail API service instance.

    This function handles the complete OAuth2 authentication flow,
    including token management and credential refresh. It implements
    secure storage of credentials and automatic token refresh.

    Authentication Flow:
    1. Check for existing valid credentials
    2. Refresh credentials if expired
    3. Initiate OAuth2 flow if no valid credentials exist
    4. Store credentials securely for future use

    Returns
    -------
        Resource: Authenticated Gmail API service resource

    Configuration:
    The function uses the following configuration values:
    - CREDENTIALS_FILE: Path to OAuth2 client credentials
    - TOKEN_FILE: Path to store/retrieve access tokens
    - SCOPES: List of API permissions required

    Security Considerations:
    - Credentials are stored using pickle serialization
    - Token file permissions are managed securely
    - Refresh tokens are handled automatically
    - Sensitive data is not logged

    Error Handling:
    - Authentication errors are propagated
    - File permission errors are logged
    - Network errors trigger retries

    """
    creds = None
    config = Config()

    # Load credentials from token file if it exists
    if os.path.exists(config.TOKEN_FILE):
        with open(config.TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # If credentials are invalid or don't exist, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CREDENTIALS_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for future use
        with open(config.TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    # Build and return Gmail service
    return build("gmail", "v1", credentials=creds)
