# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Gmail history sync functionality."""

import base64  # Add base64 import
import random
import time

import pytz  # Add pytz import
import redis
import sentry_sdk
import structlog
from database.models import Email, EmailLabelHistory, EventLog, RawEmail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from email_processing.gmail_auth import get_gmail_service
from googleapiclient.errors import HttpError

logger = structlog.get_logger(__name__)

# Constants for error handling
MAX_CONSECUTIVE_ERRORS = 5  # Maximum number of consecutive errors before shutdown
MAX_TOTAL_ERRORS = 20  # Maximum total errors in a sync session before shutdown
ERROR_COOLDOWN = 7200  # 2 hour cooldown after quota exceeded

# Rate limiting constants
MAX_REQUESTS_PER_MINUTE = 250  # Gmail's quota
WINDOW_DURATION = 60  # seconds
MIN_BACKOFF_SECONDS = 300  # Start with 5 minutes
MAX_BACKOFF_SECONDS = 7200  # Max backoff of 2 hours
BACKOFF_FACTOR = 4  # More aggressive multiplication

# Redis client for shared rate limit state
redis_client = redis.from_url(settings.CELERY_BROKER_URL)
RATE_LIMIT_KEY = "gmail_api_rate_limit"
ERROR_TIME_KEY = "gmail_api_error_time"
BACKOFF_KEY = "gmail_api_backoff"
WORKER_LOCK_KEY = "gmail_api_worker_lock"

# Tracking request times
request_times = []
last_error_time = None
current_backoff = MIN_BACKOFF_SECONDS


def _execute_gmail_api(request):
    """Execute a Gmail API request with rate limiting."""
    # Generate endpoint-specific lock key based on the request URL/method
    endpoint = str(request.uri)
    if "messages.list" in endpoint:
        lock_key = "gmail_api_messages_list"
    elif "messages.get" in endpoint:
        lock_key = "gmail_api_messages_get"
    elif "history.list" in endpoint:
        lock_key = "gmail_api_history_list"
    elif "getProfile" in endpoint:
        lock_key = "gmail_api_profile"
    else:
        lock_key = "gmail_api_other"

    # Add random startup delay between 1-5 seconds to prevent thundering herd
    time.sleep(random.uniform(1, 5))

    # Try to acquire endpoint-specific lock with expiration
    lock_acquired = False
    try:
        lock_acquired = redis_client.set(
            f"{WORKER_LOCK_KEY}:{lock_key}",
            "1",
            ex=WINDOW_DURATION,
            nx=True,
        )
    except redis.RedisError as e:
        logger.warning(
            "failed_to_acquire_lock",
            extra={"event": "lock_error", "error": str(e), "endpoint": lock_key},
        )
        # Continue without lock in case of Redis errors

    if not lock_acquired:
        # Another worker is handling this endpoint, add small delay
        time.sleep(random.uniform(5, 15))

    now = time.time()

    # Get shared state from Redis
    pipe = redis_client.pipeline()
    pipe.zrangebyscore(
        f"{RATE_LIMIT_KEY}:{lock_key}",
        now - WINDOW_DURATION,
        float("inf"),
    )
    pipe.get(f"{ERROR_TIME_KEY}:{lock_key}")
    pipe.get(f"{BACKOFF_KEY}:{lock_key}")
    request_times_raw, last_error_raw, current_backoff_raw = pipe.execute()

    # Parse values
    request_times = [float(t) for t in request_times_raw]
    last_error_time = float(last_error_raw) if last_error_raw else None
    current_backoff = (
        float(current_backoff_raw) if current_backoff_raw else MIN_BACKOFF_SECONDS
    )

    # If we had a quota exceeded error recently, enforce cooldown
    if last_error_time and now - last_error_time < ERROR_COOLDOWN:
        cooldown_remaining = ERROR_COOLDOWN - (now - last_error_time)
        logger.warning(
            "in_error_cooldown",
            extra={
                "event": "rate_limit_cooldown",
                "cooldown_remaining": cooldown_remaining,
                "error_time": last_error_time,
                "endpoint": lock_key,
            },
        )
        time.sleep(cooldown_remaining)
        # Reset state after cooldown
        pipe = redis_client.pipeline()
        pipe.delete(f"{ERROR_TIME_KEY}:{lock_key}")
        pipe.set(f"{BACKOFF_KEY}:{lock_key}", MIN_BACKOFF_SECONDS)
        pipe.delete(f"{RATE_LIMIT_KEY}:{lock_key}")
        pipe.execute()
        request_times = []

    # Check if we're over the rate limit for this endpoint
    if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
        logger.warning(
            "rate_limit_exceeded",
            extra={
                "event": "rate_limit_exceeded",
                "backoff_seconds": current_backoff,
                "requests_in_window": len(request_times),
                "endpoint": lock_key,
            },
        )
        time.sleep(current_backoff)
        # Increase backoff exponentially
        new_backoff = min(current_backoff * BACKOFF_FACTOR, MAX_BACKOFF_SECONDS)
        redis_client.set(f"{BACKOFF_KEY}:{lock_key}", new_backoff)
        redis_client.delete(
            f"{RATE_LIMIT_KEY}:{lock_key}",
        )  # Clear request history after backoff
        request_times = []

    try:
        result = request.execute()
        # Add this request to history
        redis_client.zadd(f"{RATE_LIMIT_KEY}:{lock_key}", {str(now): now})
        # Cleanup old entries
        redis_client.zremrangebyscore(
            f"{RATE_LIMIT_KEY}:{lock_key}",
            0,
            now - WINDOW_DURATION,
        )
        return result
    except HttpError as e:
        if "quota" in str(e).lower() or "rate limit exceeded" in str(e).lower():
            pipe = redis_client.pipeline()
            pipe.set(f"{ERROR_TIME_KEY}:{lock_key}", now)
            pipe.set(
                f"{BACKOFF_KEY}:{lock_key}",
                max(float(current_backoff), ERROR_COOLDOWN),
            )
            pipe.execute()

            logger.exception(
                "gmail_api_quota_exceeded",
                extra={
                    "event": "quota_exceeded",
                    "error": str(e),
                    "backoff_seconds": max(float(current_backoff), ERROR_COOLDOWN),
                    "endpoint": lock_key,
                },
            )
            raise
        raise
    finally:
        if lock_acquired:
            redis_client.delete(f"{WORKER_LOCK_KEY}:{lock_key}")


def full_sync_gmail():
    """Perform a full sync of all Gmail messages.
    Used when no emails exist in the database.
    Returns (success, messages_synced).
    """
    try:
        service = get_gmail_service()
        messages_synced = 0
        consecutive_errors = 0
        total_errors = 0

        logger.info("starting_full_sync")

        # List all messages
        request = service.users().messages().list(userId="me")

        while request is not None:
            try:
                # Check error thresholds
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(
                        "sync_aborted_consecutive_errors",
                        consecutive_errors=consecutive_errors,
                    )
                    return False, messages_synced

                if total_errors >= MAX_TOTAL_ERRORS:
                    logger.error("sync_aborted_total_errors", total_errors=total_errors)
                    return False, messages_synced

                response = _execute_gmail_api(request)
                messages = response.get("messages", [])

                for message in messages:
                    message_id = message["id"]
                    try:
                        # Get full message data
                        message_data = _execute_gmail_api(
                            service.users()
                            .messages()
                            .get(userId="me", id=message_id, format="full"),
                        )

                        with transaction.atomic():
                            # Extract headers and metadata
                            headers = {}
                            if (
                                "payload" in message_data
                                and "headers" in message_data["payload"]
                            ):
                                for header in message_data["payload"]["headers"]:
                                    headers[header["name"].lower()] = header["value"]

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
                            if "payload" in message_data:
                                payload = message_data["payload"]

                                # Handle simple messages (body directly in payload)
                                if "body" in payload and "data" in payload["body"]:
                                    if payload.get("mimeType") == "text/plain":
                                        plain_body = base64.urlsafe_b64decode(
                                            payload["body"]["data"],
                                        ).decode()
                                    elif payload.get("mimeType") == "text/html":
                                        html_body = base64.urlsafe_b64decode(
                                            payload["body"]["data"],
                                        ).decode()

                                # Handle multipart messages (body in parts)
                                if "parts" in payload:
                                    for part in payload["parts"]:
                                        if (
                                            part.get("mimeType") == "text/plain"
                                            and "body" in part
                                            and "data" in part["body"]
                                        ):
                                            plain_body = base64.urlsafe_b64decode(
                                                part["body"]["data"],
                                            ).decode()
                                        elif (
                                            part.get("mimeType") == "text/html"
                                            and "body" in part
                                            and "data" in part["body"]
                                        ):
                                            html_body = base64.urlsafe_b64decode(
                                                part["body"]["data"],
                                            ).decode()

                            # Extract received date from internalDate (milliseconds since epoch)
                            received_at = timezone.datetime.fromtimestamp(
                                int(message_data["internalDate"]) / 1000,
                                tz=pytz.UTC,
                            )

                            # Determine email category and flags
                            labels = message_data.get("labelIds", [])
                            category = "inbox"
                            if "SENT" in labels:
                                category = "sent"
                            elif "DRAFT" in labels:
                                category = "draft"
                            elif "SPAM" in labels:
                                category = "spam"
                            elif "TRASH" in labels:
                                category = "trash"

                            # Create or update email record
                            email, created = Email.objects.update_or_create(
                                gmail_id=message_id,
                                defaults={
                                    "thread_id": message_data.get("threadId"),
                                    "history_id": message_data.get("historyId"),
                                    "labels": labels,
                                    "received_at": received_at,
                                    "subject": headers.get("subject", ""),
                                    "snippet": message_data.get("snippet", ""),
                                    "from_email": from_email,
                                    "from_name": from_name,
                                    "to_emails": to_emails,
                                    "cc_emails": cc_emails,
                                    "bcc_emails": bcc_emails,
                                    "raw_content": str(message_data),
                                    "plain_body": plain_body,
                                    "html_body": html_body,
                                    "size_estimate": message_data.get(
                                        "sizeEstimate",
                                        0,
                                    ),
                                    "category": category,
                                    "importance": 1,  # Default to normal importance
                                    "status": "new",
                                    "is_draft": "DRAFT" in labels,
                                    "is_sent": "SENT" in labels,
                                    "is_read": "UNREAD" not in labels,
                                    "is_starred": "STARRED" in labels,
                                    "is_trashed": "TRASH" in labels,
                                    "email_metadata": {
                                        "message_id": headers.get("message-id", ""),
                                        "in_reply_to": headers.get("in-reply-to", ""),
                                        "references": headers.get("references", ""),
                                        "content_type": headers.get("content-type", ""),
                                    },
                                    "last_sync_at": timezone.now(),
                                },
                            )

                            # Store raw email data
                            RawEmail.objects.update_or_create(
                                gmail_message_id=message_id,
                                defaults={
                                    "thread_id": message_data.get("threadId"),
                                    "history_id": message_data.get("historyId"),
                                    "raw_data": message_data,
                                },
                            )

                            messages_synced += 1
                            consecutive_errors = (
                                0  # Reset consecutive errors on success
                            )

                    except Exception as e:
                        consecutive_errors += 1
                        total_errors += 1
                        logger.exception(
                            "message_sync_failed",
                            message_id=message_id,
                            error=str(e),
                            error_type=type(e).__name__,
                            consecutive_errors=consecutive_errors,
                            total_errors=total_errors,
                        )
                        EventLog.objects.create(
                            event_type="SYNC_ERROR",
                            details={
                                "error_message": str(e),
                                "error_type": type(e).__name__,
                                "message_id": message_id,
                                "consecutive_errors": consecutive_errors,
                                "total_errors": total_errors,
                            },
                        )
                        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            break

                request = service.users().messages().list_next(request, response)

            except Exception as e:
                consecutive_errors += 1
                total_errors += 1
                logger.exception(
                    "batch_processing_error",
                    error_type=type(e).__name__,
                    error=str(e),
                    consecutive_errors=consecutive_errors,
                    total_errors=total_errors,
                )
                EventLog.objects.create(
                    event_type="SYNC_ERROR",
                    details={
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "consecutive_errors": consecutive_errors,
                        "total_errors": total_errors,
                    },
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    break

        success = (
            consecutive_errors < MAX_CONSECUTIVE_ERRORS
            and total_errors < MAX_TOTAL_ERRORS
        )
        logger.info(
            "full_sync_completed",
            messages_synced=messages_synced,
            success=success,
            total_errors=total_errors,
        )
        return success, messages_synced

    except Exception as e:
        logger.exception("full_sync_failed", error_type=type(e).__name__, error=str(e))
        EventLog.objects.create(
            event_type="SYNC_ERROR",
            details={
                "error_message": str(e),
                "error_type": type(e).__name__,
            },
        )
        return False, 0


def sync_gmail_history(start_history_id=None):
    """Sync Gmail history from a given history ID.
    If no history ID is provided, gets the latest one from Gmail.
    If no emails exist in database, performs a full sync instead.
    Returns (success, messages_updated, pages_processed).
    """
    try:
        # Set sync context in Sentry
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("sync_type", "incremental" if start_history_id else "full")
            scope.set_context(
                "sync_info",
                {
                    "start_history_id": start_history_id,
                    "has_existing_emails": Email.objects.exists(),
                },
            )

        # Check if we have any emails in the database
        if not Email.objects.exists():
            logger.info("no_emails_found_starting_full_sync")
            success, messages_synced = full_sync_gmail()
            return success, messages_synced, 1

        service = get_gmail_service()
        pages_processed = 0
        messages_updated = 0
        consecutive_errors = 0
        total_errors = 0

        # If no start_history_id provided, get current one from Gmail
        if not start_history_id:
            profile = _execute_gmail_api(service.users().getProfile(userId="me"))
            start_history_id = profile.get("historyId")

        logger.info("starting_incremental_sync", history_id=start_history_id)

        # List history from the start_history_id
        request = (
            service.users().history().list(userId="me", startHistoryId=start_history_id)
        )

        while request is not None:
            try:
                # Check error thresholds
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(
                        "sync_aborted_consecutive_errors",
                        consecutive_errors=consecutive_errors,
                    )
                    return False, messages_updated, pages_processed

                if total_errors >= MAX_TOTAL_ERRORS:
                    logger.error("sync_aborted_total_errors", total_errors=total_errors)
                    return False, messages_updated, pages_processed

                response = _execute_gmail_api(request)
                history_list = response.get("history", [])

                for history in history_list:
                    try:
                        if process_history_item(service, history):
                            messages_updated += 1
                            consecutive_errors = 0  # Reset on success
                    except Exception as e:
                        consecutive_errors += 1
                        total_errors += 1
                        logger.exception(
                            "history_item_processing_error",
                            error_type=type(e).__name__,
                            error=str(e),
                            history_id=history.get("id"),
                            consecutive_errors=consecutive_errors,
                            total_errors=total_errors,
                        )
                        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            break

                pages_processed += 1
                request = service.users().history().list_next(request, response)

            except Exception as e:
                consecutive_errors += 1
                total_errors += 1
                logger.exception(
                    "page_processing_error",
                    error_type=type(e).__name__,
                    error=str(e),
                    history_id=start_history_id,
                    consecutive_errors=consecutive_errors,
                    total_errors=total_errors,
                )
                # Create error event
                EventLog.objects.create(
                    event_type="SYNC_ERROR",
                    details={
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "history_id": start_history_id,
                        "consecutive_errors": consecutive_errors,
                        "total_errors": total_errors,
                    },
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    break

        success = (
            consecutive_errors < MAX_CONSECUTIVE_ERRORS
            and total_errors < MAX_TOTAL_ERRORS
        )
        logger.info(
            "sync_completed",
            history_id=start_history_id,
            pages_processed=pages_processed,
            messages_updated=messages_updated,
            success=success,
            total_errors=total_errors,
        )

        return success, messages_updated, pages_processed

    except Exception as e:
        logger.exception(
            "sync_failed",
            error_type=type(e).__name__,
            error=str(e),
            history_id=start_history_id,
        )
        # Create error event
        EventLog.objects.create(
            event_type="SYNC_ERROR",
            details={
                "error_message": str(e),
                "error_type": type(e).__name__,
                "history_id": start_history_id,
            },
        )
        return False, 0, 0


def process_history_item(service, history):
    """Process a single history item.
    Returns True if any updates were made, False otherwise.
    """
    try:
        history_id = history.get("id")
        updated = False

        # Get message ID from any available source
        message_id = None
        for source in ["messages", "messagesAdded", "messagesDeleted"]:
            if history.get(source):
                message_data = history[source][0]
                message_id = message_data.get("id") or message_data.get(
                    "message",
                    {},
                ).get("id")
                if message_id:
                    break

        if not message_id:
            return False

        # Extract label changes
        labels_added = []
        labels_removed = []

        if "labelsAdded" in history:
            for label_change in history["labelsAdded"]:
                if label_change.get("message", {}).get("id") == message_id:
                    labels_added.extend(label_change["labelIds"])

        if "labelsRemoved" in history:
            for label_change in history["labelsRemoved"]:
                if label_change.get("message", {}).get("id") == message_id:
                    labels_removed.extend(label_change["labelIds"])

        # Get full message data if available
        try:
            message_data = _execute_gmail_api(
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full"),
            )

            # Extract headers and metadata
            headers = {}
            if "payload" in message_data and "headers" in message_data["payload"]:
                for header in message_data["payload"]["headers"]:
                    headers[header["name"].lower()] = header["value"]

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
            if "payload" in message_data:
                payload = message_data["payload"]

                # Handle simple messages (body directly in payload)
                if "body" in payload and "data" in payload["body"]:
                    if payload.get("mimeType") == "text/plain":
                        plain_body = base64.urlsafe_b64decode(
                            payload["body"]["data"],
                        ).decode()
                    elif payload.get("mimeType") == "text/html":
                        html_body = base64.urlsafe_b64decode(
                            payload["body"]["data"],
                        ).decode()

                # Handle multipart messages (body in parts)
                if "parts" in payload:
                    for part in payload["parts"]:
                        if (
                            part.get("mimeType") == "text/plain"
                            and "body" in part
                            and "data" in part["body"]
                        ):
                            plain_body = base64.urlsafe_b64decode(
                                part["body"]["data"],
                            ).decode()
                        elif (
                            part.get("mimeType") == "text/html"
                            and "body" in part
                            and "data" in part["body"]
                        ):
                            html_body = base64.urlsafe_b64decode(
                                part["body"]["data"],
                            ).decode()

            # Extract received date from internalDate (milliseconds since epoch)
            received_at = timezone.datetime.fromtimestamp(
                int(message_data["internalDate"]) / 1000,
                tz=pytz.UTC,
            )

        except Exception as e:
            if "HttpError 404" in str(e):
                # Message has been permanently deleted from Gmail
                logger.info("message_permanently_deleted", message_id=message_id)
                # Mark email as deleted in our database if it exists
                email = Email.objects.filter(gmail_id=message_id).first()
                if email:
                    email.soft_delete()
                    EventLog.objects.create(
                        event_type="EMAIL_DELETED",
                        email=email,
                        details={
                            "reason": "permanently_deleted_from_gmail",
                            "history_id": history_id,
                        },
                    )
                return True
            # Other errors should still be logged as warnings
            logger.warning(
                "failed_to_fetch_message",
                message_id=message_id,
                error=str(e),
            )
            message_data = None
            received_at = None
            headers = {}

        # Update email and create/update raw email record
        with transaction.atomic():
            email = Email.objects.filter(gmail_id=message_id).first()
            if email:
                # Update history ID
                email.history_id = history_id

                # Update metadata if we have full message data
                if message_data:
                    email.subject = headers.get("subject", email.subject)
                    email.snippet = message_data.get("snippet", email.snippet)
                    email.from_email = from_email
                    email.from_name = from_name
                    email.to_emails = to_emails or email.to_emails
                    email.cc_emails = cc_emails or email.cc_emails
                    email.bcc_emails = bcc_emails or email.bcc_emails
                    email.plain_body = plain_body or email.plain_body
                    email.html_body = html_body or email.html_body
                    email.received_at = received_at or email.received_at
                    email.size_estimate = message_data.get(
                        "sizeEstimate",
                        email.size_estimate,
                    )
                    email.email_metadata = {
                        "message_id": headers.get("message-id", ""),
                        "in_reply_to": headers.get("in-reply-to", ""),
                        "references": headers.get("references", ""),
                        "content_type": headers.get("content-type", ""),
                    }

                # Update labels and flags
                if labels_added or labels_removed:
                    current_labels = set(email.labels or [])
                    current_labels.update(labels_added)
                    current_labels.difference_update(labels_removed)
                    email.labels = list(current_labels)

                    # Update flags based on label changes
                    email.is_read = "UNREAD" not in current_labels
                    email.is_starred = "STARRED" in current_labels
                    email.is_trashed = "TRASH" in current_labels

                    # Update category based on labels
                    if "SENT" in current_labels:
                        email.category = "sent"
                    elif "DRAFT" in current_labels:
                        email.category = "draft"
                    elif "SPAM" in current_labels:
                        email.category = "spam"
                    elif "TRASH" in current_labels:
                        email.category = "trash"
                    else:
                        email.category = "inbox"

                    # Create label history records
                    for label in labels_added:
                        EmailLabelHistory.objects.create(
                            email=email,
                            label_id=label,
                            action="ADDED",
                            changed_by="system",
                        )

                    for label in labels_removed:
                        EmailLabelHistory.objects.create(
                            email=email,
                            label_id=label,
                            action="REMOVED",
                            changed_by="system",
                        )

                email.last_sync_at = timezone.now()
                email.save()
                updated = True

                # Update or create raw email record if we have message data
                if message_data:
                    RawEmail.objects.update_or_create(
                        gmail_message_id=message_id,
                        defaults={
                            "thread_id": message_data.get("threadId"),
                            "history_id": history_id,
                            "raw_data": message_data,
                        },
                    )

        return updated

    except Exception as e:
        logger.exception(
            "process_history_item_failed",
            error_type=type(e).__name__,
            error=str(e),
            history_id=history.get("id"),
        )
        # Create error event
        EventLog.objects.create(
            event_type="SYNC_ERROR",
            details={
                "error_message": str(e),
                "error_type": type(e).__name__,
                "history_id": history.get("id"),
                "message_id": message_id if "message_id" in locals() else None,
            },
        )
        return False
