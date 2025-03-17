"""Gmail History API synchronization module."""

import structlog
from django.utils import timezone
from django.db import transaction
from database.models import Email, RawEmail, EventLog, EmailLabelHistory
from .gmail_auth import get_gmail_credentials
import base64
from googleapiclient.discovery import build
import pytz

logger = structlog.get_logger(__name__)


class GmailHistorySync:
    """Handles synchronization of Gmail changes using the History API."""

    def __init__(self):
        self.service = None
        self.last_history_id = None
        self._current_history_id = None

    def initialize(self):
        """Initialize the Gmail service."""
        try:
            credentials = get_gmail_credentials()
            self.service = build("gmail", "v1", credentials=credentials)

            # Get the last history ID we processed
            latest_email = Email.objects.order_by("-last_sync_at").first()
            if latest_email and latest_email.history_id:
                self.last_history_id = latest_email.history_id
                logger.info(
                    "history_id_found",
                    msg=f"Found last history ID: {self.last_history_id}",
                    history_id=self.last_history_id,
                )
            else:
                # If no history ID found, get the current one from Gmail
                profile = self.service.users().getProfile(userId="me").execute()
                self.last_history_id = profile.get("historyId")
                logger.info(
                    "using_current_history_id",
                    msg=f"Using current Gmail history ID: {self.last_history_id}",
                    history_id=self.last_history_id,
                )

            if not self.last_history_id:
                raise ValueError("Could not determine history ID")

            return self

        except Exception as e:
            logger.error(
                "initialization_failed", error=str(e), error_type=type(e).__name__
            )
            raise

    def sync_changes(self):
        """Sync changes from Gmail using History API."""
        if not self.last_history_id:
            logger.warning(
                "no_history_id_found", msg="No history ID found, cannot sync changes"
            )
            raise ValueError("No history ID found")

        try:
            # List history of all changes
            request = (
                self.service.users()
                .history()
                .list(userId="me", startHistoryId=self.last_history_id)
            )

            while request is not None:
                try:
                    history_list = request.execute()

                    if "history" not in history_list:
                        logger.info("no_changes_found", msg="No changes to sync")
                        break

                    for history in history_list["history"]:
                        try:
                            self._process_history_record(history)
                            # Update the last history ID after each record is processed
                            if "id" in history:
                                self.last_history_id = history["id"]
                        except Exception as e:
                            logger.error(
                                "history_record_processing_failed",
                                error=str(e),
                                error_type=type(e).__name__,
                                history_id=history.get("id"),
                                last_history_id=self.last_history_id,
                            )
                            raise

                    # Get the next page
                    request = (
                        self.service.users().history().list_next(request, history_list)
                    )

                except Exception as e:
                    logger.error(
                        "history_list_processing_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        last_history_id=self.last_history_id,
                    )
                    # Create error event log
                    EventLog.objects.create(
                        event_type="SYNC_ERROR",
                        details={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "last_history_id": self.last_history_id,
                        },
                    )
                    raise

        except Exception as e:
            # Only log at the top level if it's not already logged
            if not isinstance(e, Exception) or "API Error" not in str(e):
                logger.error(
                    "sync_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    last_history_id=self.last_history_id,
                )
                # Create error event log
                EventLog.objects.create(
                    event_type="SYNC_ERROR",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "last_history_id": self.last_history_id,
                    },
                )
            raise

    def _process_history_record(self, history):
        """Process a single history record."""
        self._current_history_id = history["id"]
        affected_message_ids = set()

        try:
            # Get all message IDs from the history record
            if "messages" in history:
                for msg in history["messages"]:
                    affected_message_ids.add(msg["id"])

            # Process messages that were added
            if "messagesAdded" in history:
                for msg_add in history["messagesAdded"]:
                    msg_id = msg_add["message"]["id"]
                    affected_message_ids.add(msg_id)
                    try:
                        self._handle_message_added(msg_add["message"])
                    except Exception as e:
                        logger.error(
                            "message_add_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            gmail_id=msg_id,
                        )
                        raise

            # Process messages that were deleted
            if "messagesDeleted" in history:
                for msg_del in history["messagesDeleted"]:
                    msg_id = msg_del["message"]["id"]
                    affected_message_ids.add(msg_id)
                    try:
                        self._handle_message_deleted(msg_del["message"])
                    except Exception as e:
                        logger.error(
                            "message_delete_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            gmail_id=msg_id,
                        )
                        raise

            # Process label changes
            if "labelsAdded" in history:
                for label_add in history["labelsAdded"]:
                    msg_id = label_add["message"]["id"]
                    affected_message_ids.add(msg_id)
                    try:
                        self._handle_label_added(
                            label_add["message"], label_add["labelIds"]
                        )
                    except Exception as e:
                        logger.error(
                            "label_add_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            gmail_id=msg_id,
                        )
                        raise

            if "labelsRemoved" in history:
                for label_rem in history["labelsRemoved"]:
                    msg_id = label_rem["message"]["id"]
                    affected_message_ids.add(msg_id)
                    try:
                        self._handle_label_removed(
                            label_rem["message"], label_rem["labelIds"]
                        )
                    except Exception as e:
                        logger.error(
                            "label_remove_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            gmail_id=msg_id,
                        )
                        raise

            # Update history ID for all affected messages
            for msg_id in affected_message_ids:
                try:
                    email = Email.objects.get(gmail_id=msg_id)
                    if (
                        not email.is_deleted
                    ):  # Only update history ID for non-deleted messages
                        email.history_id = self._current_history_id
                        email.last_sync_at = timezone.now()
                        email.save()
                except Email.DoesNotExist:
                    logger.warning(
                        "email_not_found",
                        msg=f"Email {msg_id} not found for history update",
                        gmail_id=msg_id,
                    )

        except Exception as e:
            logger.error(
                "history_record_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                history_id=history.get("id"),
                last_history_id=self.last_history_id,
            )
            raise

        return affected_message_ids

    def _handle_message_added(self, message):
        """Handle a new message being added."""
        try:
            # Get full message details from Gmail
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message["id"])
                .execute()
            )

            # Check if message already exists
            try:
                email = Email.objects.get(gmail_id=msg["id"])
                # Don't update history ID for existing messages
                email.last_sync_at = timezone.now()
                email.save()
                return
            except Email.DoesNotExist:
                pass

            # Create new email
            email = Email.objects.create(
                gmail_id=msg["id"],
                thread_id=msg.get("threadId"),
                history_id=self._current_history_id,
                subject=next(
                    (
                        h["value"]
                        for h in msg["payload"]["headers"]
                        if h["name"].lower() == "subject"
                    ),
                    "",
                ),
                snippet=msg.get("snippet", ""),
                from_email=next(
                    (
                        h["value"]
                        for h in msg["payload"]["headers"]
                        if h["name"].lower() == "from"
                    ),
                    "",
                ),
                to_emails=[
                    h["value"]
                    for h in msg["payload"]["headers"]
                    if h["name"].lower() == "to"
                ],
                received_at=timezone.now(),
                status="new",
                category="inbox",
                labels=msg.get("labelIds", []),
                last_sync_at=timezone.now(),
            )

            # Create event log
            EventLog.objects.create(
                email=email,
                event_type="EMAIL_ADDED",
                details={
                    "gmail_id": msg["id"],
                    "thread_id": msg.get("threadId"),
                    "history_id": self._current_history_id,
                },
            )

            return email

        except Exception as e:
            logger.error(
                "message_add_failed",
                error=str(e),
                error_type=type(e).__name__,
                gmail_id=message["id"],
            )
            raise

    def _handle_message_deleted(self, message):
        """Handle a message that was deleted from the mailbox."""
        try:
            email = Email.objects.get(gmail_id=message["id"])
            email.is_deleted = True
            email.history_id = self._current_history_id
            email.last_sync_at = timezone.now()
            email.save()

            # Create event log
            EventLog.objects.create(
                email=email,
                event_type="EMAIL_DELETED",
                details={
                    "gmail_id": message["id"],
                    "history_id": self._current_history_id,
                },
            )

            return email

        except Email.DoesNotExist:
            logger.warning(
                "email_not_found_for_deletion",
                msg=f"Email {message['id']} not found for deletion",
                gmail_id=message["id"],
            )
        except Exception as e:
            logger.error(
                "message_delete_failed",
                error=str(e),
                error_type=type(e).__name__,
                gmail_id=message["id"],
            )
            raise

    def _handle_label_added(self, message, label_ids):
        """Handle labels being added to a message."""
        try:
            email = Email.objects.get(gmail_id=message["id"])
            current_labels = set(email.labels or [])
            new_labels = set(label_ids)

            # Only update if there are new labels
            if new_labels - current_labels:
                email.labels = list(current_labels | new_labels)
                email.history_id = self._current_history_id
                email.last_sync_at = timezone.now()
                email.save()

                # Record label changes
                for label_id in new_labels - current_labels:
                    EmailLabelHistory.objects.create(
                        email=email, label_id=label_id, action="added"
                    )

                logger.info(
                    "labels_added",
                    msg=f"Added labels {new_labels - current_labels} to email {message['id']}",
                    gmail_id=message["id"],
                    labels=list(new_labels - current_labels),
                )
        except Email.DoesNotExist:
            logger.warning(
                "email_not_found",
                msg=f"Email {message['id']} not found for label addition",
                gmail_id=message["id"],
            )

    def _handle_label_removed(self, message, label_ids):
        """Handle labels being removed from a message."""
        try:
            email = Email.objects.get(gmail_id=message["id"])
            current_labels = set(email.labels or [])
            removed_labels = set(label_ids)

            # Only update if there are labels to remove
            if removed_labels & current_labels:
                email.labels = list(current_labels - removed_labels)
                email.history_id = self._current_history_id
                email.last_sync_at = timezone.now()
                email.save()

                # Record label changes
                for label_id in removed_labels & current_labels:
                    EmailLabelHistory.objects.create(
                        email=email, label_id=label_id, action="removed"
                    )

                logger.info(
                    "labels_removed",
                    msg=f"Removed labels {removed_labels & current_labels} from email {message['id']}",
                    gmail_id=message["id"],
                    labels=list(removed_labels & current_labels),
                )
        except Email.DoesNotExist:
            logger.warning(
                "email_not_found",
                msg=f"Email {message['id']} not found for label removal",
                gmail_id=message["id"],
            )
