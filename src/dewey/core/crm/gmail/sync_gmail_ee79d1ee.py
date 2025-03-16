# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Management command for initial Gmail sync."""
from __future__ import annotations

import email.utils

import pytz
import structlog
from database.models import Email, EventLog, RawEmail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from email_processing.gmail_auth import get_gmail_service
from tqdm import tqdm

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Initial sync of Gmail messages"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=50,
            help="Number of messages to process in each batch",
        )
        parser.add_argument(
            "--max-messages",
            dest="max_messages",
            type=int,
            default=1000,
            help="Maximum number of messages to sync",
        )

    def handle(self, *args, **options) -> None:
        batch_size = options["batch_size"]
        max_messages = options["max_messages"]

        try:
            service = get_gmail_service()

            # List all messages with pagination
            messages = []
            next_page_token = None

            while True:
                # Get next page of messages
                results = (
                    service.users()
                    .messages()
                    .list(
                        userId="me",
                        maxResults=min(
                            500,
                            max_messages - len(messages),
                        ),  # Gmail API max is 500
                        pageToken=next_page_token,
                    )
                    .execute()
                )

                if "messages" in results:
                    messages.extend(results["messages"])

                # Check if we have enough messages
                if len(messages) >= max_messages:
                    messages = messages[:max_messages]  # Trim to max_messages
                    break

                # Check for more pages
                next_page_token = results.get("nextPageToken")
                if not next_page_token:
                    break

            self.stdout.write(f"Found {len(messages)} messages in Gmail")

            # Process messages in batches with progress bar
            with tqdm(total=len(messages), desc="Syncing emails") as pbar:
                processed = 0
                new_messages = 0
                errors = 0

                for i in range(0, len(messages), batch_size):
                    batch = messages[i : i + batch_size]

                    for message in batch:
                        try:
                            if self._process_message(service, message["id"]):
                                new_messages += 1
                        except Exception as e:
                            errors += 1
                            logger.exception(
                                "message_processing_failed",
                                gmail_id=message["id"],
                                error=str(e),
                                error_type=type(e).__name__,
                            )
                        processed += 1
                        pbar.update(1)

            self.stdout.write(
                f"Sync completed: {processed} messages processed, {new_messages} new, {errors} errors",
            )

        except Exception as e:
            self.stderr.write(f"Error during sync: {e!s}")
            raise

    def _process_message(self, service, gmail_id) -> bool | None:
        """Process a single message. Returns True if new message was processed."""
        try:
            # Skip if already exists
            if Email.objects.filter(gmail_id=gmail_id).exists():
                logger.debug("message_already_exists", gmail_id=gmail_id)
                return False

            # Fetch full message
            full_msg = (
                service.users()
                .messages()
                .get(userId="me", id=gmail_id, format="full")
                .execute()
            )

            # Extract headers
            headers = {
                h["name"].lower(): h["value"]
                for h in full_msg.get("payload", {}).get("headers", [])
            }

            # Parse received date with better timezone handling
            received_at = timezone.now()  # Default to now
            date_str = headers.get("date")
            if date_str:
                try:
                    # Parse with email.utils (handles most RFC email date formats)
                    parsed_date = email.utils.parsedate_to_datetime(date_str)
                    if parsed_date.tzinfo is None:
                        # If timezone naive, assume UTC
                        received_at = pytz.UTC.localize(parsed_date)
                    else:
                        # If already has timezone, convert to UTC
                        received_at = parsed_date.astimezone(pytz.UTC)
                except (TypeError, ValueError) as e:
                    logger.warning(
                        "date_parse_failed",
                        gmail_id=gmail_id,
                        date_str=date_str,
                        error=str(e),
                    )

            # Extract email addresses safely
            from_email = headers.get("from", "")
            try:
                # Try to extract email from "Name <email@domain.com>" format
                if "<" in from_email:
                    from_email = from_email.split("<")[-1].strip(">")
            except Exception as e:
                logger.warning(
                    "from_email_parse_failed",
                    gmail_id=gmail_id,
                    from_str=headers.get("from", ""),
                    error=str(e),
                )

            # Parse to_emails more safely
            to_emails = []
            if headers.get("to"):
                for addr in headers["to"].split(","):
                    addr = addr.strip()
                    try:
                        if "<" in addr:
                            email_addr = addr.split("<")[-1].strip(">")
                        else:
                            email_addr = addr
                        if "@" in email_addr:
                            to_emails.append(email_addr)
                    except Exception as e:
                        logger.warning(
                            "to_email_parse_failed",
                            gmail_id=gmail_id,
                            address=addr,
                            error=str(e),
                        )

            # Use a separate transaction for raw email and processed email
            with transaction.atomic():
                # Store raw email first
                RawEmail.objects.create(
                    gmail_message_id=gmail_id,
                    thread_id=full_msg["threadId"],
                    history_id=full_msg["historyId"],
                    raw_data=full_msg,
                )

                # Create processed email
                email_obj = Email.objects.create(
                    gmail_id=gmail_id,
                    thread_id=full_msg["threadId"],
                    history_id=full_msg["historyId"],
                    subject=headers.get("subject", ""),
                    from_email=from_email,
                    to_emails=to_emails,
                    raw_content=full_msg.get("snippet", ""),
                    received_at=received_at,
                    email_metadata={
                        "headers": headers,
                        "size": full_msg.get("sizeEstimate", 0),
                        "message_id": headers.get("message-id", ""),
                        "references": headers.get("references", ""),
                        "in_reply_to": headers.get("in-reply-to", ""),
                    },
                )

            # Log event outside the transaction to prevent rollback issues
            EventLog.objects.create(
                event_type="EMAIL_PROCESSED",
                email=email_obj,
                details={
                    "gmail_id": gmail_id,
                    "subject": email_obj.subject,
                    "from_email": email_obj.from_email,
                    "history_id": email_obj.history_id,
                    "date": email_obj.received_at.isoformat(),
                },
            )

            return True

        except Exception as e:
            logger.exception(
                "message_processing_failed",
                gmail_id=gmail_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
