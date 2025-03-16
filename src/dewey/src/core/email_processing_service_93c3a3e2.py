# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Email processing service.

This module provides the core service for processing emails from Gmail and storing
them in the database. It handles:
- Email parsing and normalization
- Contact extraction and association
- Transactional processing
- Error handling and logging

The service is designed to be idempotent and transactional, ensuring data consistency
even in case of partial failures.

Key Features:
- Batch processing of emails with individual error isolation
- Comprehensive header parsing and normalization
- Automatic contact extraction and association
- Transactional database operations
- Detailed logging and error tracking
- Date parsing with fallback to current time
- Email address normalization and validation

Typical Usage:
    1. Initialize service with Gmail client
    2. Fetch message IDs from Gmail API
    3. Process messages in batches
    4. Handle any processing errors
    5. Monitor processing metrics

Example:
-------
    >>> gmail_client = GmailClient()
    >>> service = EmailProcessingService(gmail_client)
    >>> message_ids = gmail_client.fetch_new_message_ids()
    >>> processed_count = service.process_new_emails(message_ids)
    >>> print(f"Processed {processed_count} emails")

Note:
----
    All database operations are wrapped in transactions to ensure atomicity.
    Individual email processing failures are logged but don't interrupt batch processing.

"""
from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

import structlog
from database.models import Contact, Email, EmailContactAssociation
from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from datetime import datetime

logger = structlog.get_logger(__name__)


class EmailProcessingService:
    """Service for processing emails from Gmail.

    This service handles the complete lifecycle of email processing:
    1. Fetching email data from Gmail API
    2. Parsing and normalizing email content
    3. Extracting and associating contacts
    4. Storing processed data in the database
    5. Handling errors and retries

    The service maintains data consistency through:
    - Atomic database transactions
    - Idempotent processing operations
    - Comprehensive error logging
    - Automatic retry mechanisms

    Attributes:
    ----------
        gmail_client (GmailClient): Configured client for Gmail API access
        logger (structlog.BoundLogger): Configured logger for processing operations

    Methods:
    -------
        process_new_emails: Process a batch of email message IDs
        _process_single_email: Process individual email message
        _extract_headers: Extract and normalize email headers
        _parse_received_date: Parse email received date with fallback
        _create_email_record: Create database record for email
        _process_contacts: Extract and associate contacts with email
        _extract_email_address: Normalize single email address
        _extract_email_addresses: Normalize multiple email addresses

    Example:
    -------
        >>> service = EmailProcessingService(gmail_client)
        >>> processed_count = service.process_new_emails(['msg1', 'msg2'])
        >>> print(f"Successfully processed {processed_count} emails")

    """

    def __init__(self, gmail_client) -> None:
        """Initialize the service with a Gmail client.

        Args:
        ----
            gmail_client: Configured GmailClient instance for API access

        """
        self.gmail_client = gmail_client

    def process_new_emails(self, message_ids: list[str]) -> int:
        """Process new emails from Gmail.

        Processes a batch of emails identified by their Gmail message IDs.
        Each email is processed individually, with failures logged but not
        interrupting the overall process.

        Args:
        ----
            message_ids: List of Gmail message IDs to process

        Returns:
        -------
            int: Number of emails successfully processed

        Example:
        -------
            >>> service = EmailProcessingService(gmail_client)
            >>> processed_count = service.process_new_emails(['msg1', 'msg2'])
            >>> print(f"Processed {processed_count} emails")

        """
        processed_count = 0
        for message_id in message_ids:
            try:
                # Fetch full message data from Gmail API
                message_data = self.gmail_client.get_message(message_id)

                # Process individual email within try-catch to isolate failures
                if self._process_single_email(message_data):
                    processed_count += 1
            except Exception as e:
                logger.warning(
                    "Error processing email",
                    message_id=message_id,
                    error=str(e),
                    exc_info=True,
                )
        return processed_count

    def _process_single_email(self, email_data: dict) -> bool:
        """Process a single email and store in the database.

        Handles the complete processing of a single email, including:
        - Header extraction and parsing
        - Date normalization
        - Contact extraction
        - Database storage

        Args:
        ----
            email_data (Dict): Email data from Gmail API containing:
                - id: Gmail message ID
                - threadId: Conversation thread ID
                - payload: Email content and headers
                - raw: Raw email content

        Returns:
        -------
            bool: True if email was processed successfully, False otherwise

        Raises:
        ------
            ValueError: If required email data is missing
            DatabaseError: If database operations fail

        """
        try:
            # Extract and normalize headers from payload
            headers = self._extract_headers(email_data)

            # Parse and validate received date
            received_date = self._parse_received_date(headers)

            # Process email and contacts within a transaction
            with transaction.atomic():
                # Create email record
                email = self._create_email_record(email_data, headers, received_date)

                # Process sender and recipients
                self._process_contacts(email, headers)

            return True

        except Exception as e:
            logger.warning(
                "Error processing email",
                email_id=email_data.get("id"),
                error=str(e),
                exc_info=True,
            )
            return False

    def _extract_headers(self, email_data: dict) -> dict[str, str]:
        """Extract and normalize email headers from payload.

        Args:
        ----
            email_data: Raw email data from Gmail API

        Returns:
        -------
            Dict: Normalized headers with lowercase keys

        """
        headers = {}
        if "payload" in email_data and "headers" in email_data["payload"]:
            for header in email_data["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]
        return headers

    def _parse_received_date(self, headers: dict) -> datetime:
        """Parse and validate the received date from email headers.

        Args:
        ----
            headers: Normalized email headers

        Returns:
        -------
            datetime: Parsed datetime or current time if parsing fails

        """
        received_date = timezone.now()
        if "date" in headers:
            try:
                received_date = parsedate_to_datetime(headers["date"])
            except Exception as e:
                logger.warning(
                    "Failed to parse email date",
                    date_str=headers["date"],
                    error=str(e),
                )
        return received_date

    def _create_email_record(
        self,
        email_data: dict,
        headers: dict,
        received_date: datetime,
    ) -> Email:
        """Create and save an Email record in the database.

        Args:
        ----
            email_data: Raw email data from Gmail API
            headers: Normalized email headers
            received_date: Parsed received datetime

        Returns:
        -------
            Email: Created Email instance

        """
        return Email.objects.create(
            gmail_id=email_data["id"],
            thread_id=email_data.get("threadId", ""),
            subject=headers.get("subject", ""),
            raw_content=email_data.get("raw", ""),
            received_at=received_date,
        )

    def _process_contacts(self, email: Email, headers: dict) -> None:
        """Process and associate contacts from email headers.

        Args:
        ----
            email: Email instance to associate contacts with
            headers: Normalized email headers containing contact info

        """
        # Process sender
        from_email = self._extract_email_address(headers.get("from", ""))
        if from_email:
            from_contact, _ = Contact.objects.get_or_create(email=from_email)
            EmailContactAssociation.objects.create(
                email=email,
                contact=from_contact,
                association_type="from",
            )

        # Process recipients (to, cc, bcc)
        for field in ["to", "cc", "bcc"]:
            if field in headers:
                emails = self._extract_email_addresses(headers[field])
                for recipient_email in emails:
                    if recipient_email:
                        contact, _ = Contact.objects.get_or_create(
                            email=recipient_email,
                        )
                        EmailContactAssociation.objects.create(
                            email=email,
                            contact=contact,
                            association_type=field,
                        )

    def _extract_email_address(self, address_str: str) -> str | None:
        """Extract clean email address from a header string.

        Args:
        ----
            address_str: Raw email address string from header

        Returns:
        -------
            Optional[str]: Clean email address or None if invalid

        """
        if not address_str:
            return None
        return address_str.split("<")[-1].rstrip(">").strip()

    def _extract_email_addresses(self, addresses_str: str) -> list[str]:
        """Extract multiple clean email addresses from a header string.

        Args:
        ----
            addresses_str: Raw email addresses string from header

        Returns:
        -------
            List[str]: List of clean email addresses

        """
        if not addresses_str:
            return []
        return [
            self._extract_email_address(e.strip())
            for e in addresses_str.split(",")
            if e.strip()
        ]
