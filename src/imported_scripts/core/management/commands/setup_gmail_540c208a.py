"""Gmail setup command."""

import pytz
import structlog
from database.models import Email, EventLog, RawEmail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from email_processing.gmail_auth import get_gmail_service

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Set up Gmail integration and fetch initial emails"

    def handle(self, *args, **options) -> None:
        try:
            # Get Gmail service
            self.stdout.write("Getting Gmail service...")
            logger.info("getting_gmail_service")
            service = get_gmail_service()

            # Fetch last 10 messages for testing
            self.stdout.write("Fetching messages...")
            logger.info("fetching_messages")
            results = (
                service.users().messages().list(userId="me", maxResults=10).execute()
            )
            messages = results.get("messages", [])
            self.stdout.write(f"Found {len(messages)} messages")
            logger.info("messages_found", count=len(messages))

            stored_count = 0
            skipped_count = 0

            for message in messages:
                try:
                    # Check if message already exists
                    if RawEmail.objects.filter(gmail_message_id=message["id"]).exists():
                        self.stdout.write(f"Skipping existing message: {message['id']}")
                        logger.info("message_skipped", gmail_id=message["id"])
                        skipped_count += 1
                        continue

                    # Fetch full message details
                    full_msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message["id"], format="full")
                        .execute()
                    )

                    # Extract headers and metadata
                    headers = {}
                    if "payload" in full_msg and "headers" in full_msg["payload"]:
                        for header in full_msg["payload"]["headers"]:
                            headers[header["name"].lower()] = header["value"]

                    # Extract received date from internalDate (milliseconds since epoch)
                    received_at = timezone.datetime.fromtimestamp(
                        int(full_msg["internalDate"]) / 1000,
                        tz=pytz.UTC,
                    )

                    # Parse email addresses
                    from_header = headers.get("from", "")
                    from_name = from_header.split("<")[0].strip().strip('"')
                    from_email = (
                        from_header.split("<")[-1].rstrip(">")
                        if "<" in from_header
                        else from_header
                    )

                    to_emails = []
                    cc_emails = []
                    bcc_emails = []

                    # Parse recipient lists
                    for field, target_list in [
                        ("to", to_emails),
                        ("cc", cc_emails),
                        ("bcc", bcc_emails),
                    ]:
                        if field in headers:
                            addresses = headers[field].split(",")
                            for addr in addresses:
                                email = (
                                    addr.split("<")[-1].rstrip(">")
                                    if "<" in addr
                                    else addr.strip()
                                )
                                if email:
                                    target_list.append(email)

                    # Extract message content
                    plain_body = ""
                    html_body = ""
                    if "payload" in full_msg:
                        for part in full_msg["payload"].get("parts", []):
                            if part.get("mimeType") == "text/plain":
                                plain_body = part.get("body", {}).get("data", "")
                            elif part.get("mimeType") == "text/html":
                                html_body = part.get("body", {}).get("data", "")

                    # Determine email category and flags
                    labels = full_msg.get("labelIds", [])
                    category = "inbox"
                    if "SENT" in labels:
                        category = "sent"
                    elif "DRAFT" in labels:
                        category = "draft"
                    elif "SPAM" in labels:
                        category = "spam"
                    elif "TRASH" in labels:
                        category = "trash"

                    with transaction.atomic():
                        # Store raw email data
                        self.stdout.write(
                            f"Processing message: {headers.get('subject', '')}",
                        )
                        logger.info(
                            "processing_message",
                            subject=headers.get("subject", ""),
                            gmail_id=message["id"],
                        )

                        RawEmail.objects.create(
                            gmail_message_id=message["id"],
                            thread_id=full_msg["threadId"],
                            history_id=full_msg["historyId"],
                            raw_data=full_msg,
                        )

                        # Create processed email record
                        email = Email.objects.create(
                            gmail_id=message["id"],
                            thread_id=full_msg["threadId"],
                            history_id=full_msg["historyId"],
                            subject=headers.get("subject", ""),
                            snippet=full_msg.get("snippet", ""),
                            from_email=from_email,
                            from_name=from_name,
                            to_emails=to_emails,
                            cc_emails=cc_emails,
                            bcc_emails=bcc_emails,
                            raw_content=str(full_msg),
                            plain_body=plain_body,
                            html_body=html_body,
                            received_at=received_at,
                            size_estimate=full_msg.get("sizeEstimate", 0),
                            labels=labels,
                            category=category,
                            importance=1,  # Default to normal importance
                            status="new",
                            is_draft="DRAFT" in labels,
                            is_sent="SENT" in labels,
                            is_read="UNREAD" not in labels,
                            is_starred="STARRED" in labels,
                            is_trashed="TRASH" in labels,
                            email_metadata={
                                "message_id": headers.get("message-id", ""),
                                "in_reply_to": headers.get("in-reply-to", ""),
                                "references": headers.get("references", ""),
                                "content_type": headers.get("content-type", ""),
                            },
                            last_sync_at=timezone.now(),
                        )

                        # Log the event
                        EventLog.objects.create(
                            event_type="EMAIL_PROCESSED",
                            email=email,
                            details={
                                "gmail_id": message["id"],
                                "subject": headers.get("subject", ""),
                                "date": received_at.isoformat(),
                            },
                            performed_by="setup_gmail",
                        )

                        stored_count += 1
                        self.stdout.write(
                            f"Successfully stored message: {headers.get('subject', '')}",
                        )
                        logger.info(
                            "message_stored",
                            subject=headers.get("subject", ""),
                            gmail_id=message["id"],
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to store message: {message['id']}"),
                    )
                    logger.exception(
                        "message_storage_failed",
                        error=str(e),
                        gmail_id=message["id"],
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully connected! Found {len(messages)} messages, stored {stored_count}, skipped {skipped_count}.",
                ),
            )
            logger.info(
                "setup_complete",
                messages_found=len(messages),
                messages_stored=stored_count,
                messages_skipped=skipped_count,
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to set up Gmail: {e}"))
            logger.exception("gmail_setup_failed", error=str(e))
            raise
