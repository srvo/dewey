"""Gmail History API synchronization module."""

from __future__ import annotations

from typing import Any

import structlog
from database.models import Email, EmailLabelHistory, EventLog
from django.utils import timezone
from googleapiclient.discovery import Resource, build

from .gmail_auth import get_gmail_credentials

logger = structlog.get_logger(__name__)


class GmailHistorySync:
    """Handles synchronization of Gmail changes using the History API."""

    def __init__(self) -> None:
        """Initializes the GmailHistorySync class."""
        self.service: Resource | None = None
        self.last_history_id: str | None = None
        self._current_history_id: str | None = None

    def initialize(self) -> GmailHistorySync:
        """Initializes the Gmail service and retrieves the last history ID.

        Returns:
            GmailHistorySync: The initialized GmailHistorySync instance.

        Raises:
            ValueError: If a history ID cannot be determined.
            Exception: If any error occurs during initialization.

        """
        try:
            credentials = get_gmail_credentials()
            self.service = build("gmail", "v1", credentials=credentials)

            latest_email = Email.objects.order_by("-last_sync_at").first()
            if latest_email and latest_email.history_id:
                self.last_history_id = latest_email.history_id
                logger.info(
                    "history_id_found",
                    msg=f"Found last history ID: {self.last_history_id}",
                    history_id=self.last_history_id,
                )
            else:
                profile = self.service.users().getProfile(userId="me").execute()
                self.last_history_id = profile.get("historyId")
                logger.info(
                    "using_current_history_id",
                    msg=f"Using current Gmail history ID: {self.last_history_id}",
                    history_id=self.last_history_id,
                )

            if not self.last_history_id:
                msg = "Could not determine history ID"
                raise ValueError(msg)

            return self

        except Exception as e:
            logger.exception(
                "initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def sync_changes(self) -> None:
        """Syncs changes from Gmail using the History API.

        Raises:
            ValueError: If no history ID is found.
            HttpError: If there's an issue with the Gmail API request.
            Exception: If any other error occurs during synchronization.

        """
        if not self.last_history_id:
            logger.warning(
                "no_history_id_found",
                msg="No history ID found, cannot sync changes",
            )
            msg = "No history ID found"
            raise ValueError(msg)

        try:
            request = (
                self.service.users()
                .history()
                .list(userId="me", startHistoryId=self.last_history_id)
            )

            while request is not None:
                history_list = self._execute_history_request(request)

                if not history_list or "history" not in history_list:
                    logger.info("no_changes_found", msg="No changes to sync")
                    break

                for history in history_list["history"]:
                    try:
                        self._process_history_record(history)
                        if "id" in history:
                            self.last_history_id = history["id"]
                    except Exception as e:
                        logger.exception(
                            "history_record_processing_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            history_id=history.get("id"),
                            last_history_id=self.last_history_id,
                        )
                        raise

                request = (
                    self.service.users().history().list_next(request, history_list)
                )

        except Exception as e:
            logger.exception(
                "sync_error",
                error=str(e),
                error_type=type(e).__name__,
                last_history_id=self.last_history_id,
            )
            EventLog.objects.create(
                event_type="SYNC_ERROR",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "last_history_id": self.last_history_id,
                },
            )
            raise

    def _execute_history_request(self, request: Any) -> dict[str, Any] | None:
        """Executes a Gmail history request and handles potential errors.

        Args:
            request: The Gmail API request object.

        Returns:
            Optional[Dict[str, Any]]: The result of the request, or None if an error occurs.

        Raises:
            HttpError: If there's an issue with the Gmail API request.
            Exception: If any other error occurs during request execution.

        """
        try:
            return request.execute()
        except Exception as e:
            logger.exception(
                "history_list_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                last_history_id=self.last_history_id,
            )
            EventLog.objects.create(
                event_type="SYNC_ERROR",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "last_history_id": self.last_history_id,
                },
            )
            raise

    def _process_history_record(self, history: dict[str, Any]) -> set[str]:
        """Processes a single history record from the Gmail API.

        Args:
            history (Dict[str, Any]): A dictionary representing a single history record.

        Returns:
            Set[str]: A set of message IDs affected by the history record.

        Raises:
            Exception: If any error occurs during the processing of the history record.

        """
        self._current_history_id = history["id"]
        affected_message_ids: set[str] = set()

        try:
            if "messages" in history:
                for msg in history["messages"]:
                    affected_message_ids.add(msg["id"])

            if "messagesAdded" in history:
                for msg_add in history["messagesAdded"]:
                    msg_id = msg_add["message"]["id"]
                    affected_message_ids.add(msg_id)
                    self._handle_message_added(msg_add["message"])

            if "messagesDeleted" in history:
                for msg_del in history["messagesDeleted"]:
                    msg_id = msg_del["message"]["id"]
                    affected_message_ids.add(msg_id)
                    self._handle_message_deleted(msg_del["message"])

            if "labelsAdded" in history:
                for label_add in history["labelsAdded"]:
                    msg_id = label_add["message"]["id"]
                    affected_message_ids.add(msg_id)
                    self._handle_label_added(
                        label_add["message"],
                        label_add["labelIds"],
                    )

            if "labelsRemoved" in history:
                for label_rem in history["labelsRemoved"]:
                    msg_id = label_rem["message"]["id"]
                    affected_message_ids.add(msg_id)
                    self._handle_label_removed(
                        label_rem["message"],
                        label_rem["labelIds"],
                    )

            self._update_history_id_for_messages(affected_message_ids)

        except Exception as e:
            logger.exception(
                "history_record_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                history_id=history.get("id"),
                last_history_id=self.last_history_id,
            )
            raise

        return affected_message_ids

    def _update_history_id_for_messages(self, message_ids: set[str]) -> None:
        """Updates the history ID for a set of messages.

        Args:
            message_ids (Set[str]): A set of message IDs to update.

        """
        for msg_id in message_ids:
            try:
                email = Email.objects.get(gmail_id=msg_id)
                if not email.is_deleted:
                    email.history_id = self._current_history_id
                    email.last_sync_at = timezone.now()
                    email.save()
            except Email.DoesNotExist:
                logger.warning(
                    "email_not_found",
                    msg=f"Email {msg_id} not found for history update",
                    gmail_id=msg_id,
                )

    def _handle_message_added(self, message: dict[str, Any]) -> Email | None:
        """Handles a new message being added.

        Args:
            message (Dict[str, Any]): A dictionary representing the added message.

        Returns:
            Optional[Email]: The created or updated Email object, or None if an error occurs.

        Raises:
            Exception: If any error occurs while handling the message addition.

        """
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message["id"])
                .execute()
            )

            try:
                email = Email.objects.get(gmail_id=msg["id"])
                email.last_sync_at = timezone.now()
                email.save()
                return None
            except Email.DoesNotExist:
                pass

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
            logger.exception(
                "message_add_failed",
                error=str(e),
                error_type=type(e).__name__,
                gmail_id=message["id"],
            )
            raise

    def _handle_message_deleted(self, message: dict[str, Any]) -> Email | None:
        """Handles a message that was deleted from the mailbox.

        Args:
            message (Dict[str, Any]): A dictionary representing the deleted message.

        Returns:
            Optional[Email]: The updated Email object, or None if the email does not exist.

        Raises:
            Exception: If any error occurs while handling the message deletion.

        """
        try:
            email = Email.objects.get(gmail_id=message["id"])
            email.is_deleted = True
            email.history_id = self._current_history_id
            email.last_sync_at = timezone.now()
            email.save()

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
            return None
        except Exception as e:
            logger.exception(
                "message_delete_failed",
                error=str(e),
                error_type=type(e).__name__,
                gmail_id=message["id"],
            )
            raise

    def _handle_label_added(
        self,
        message: dict[str, Any],
        label_ids: list[str],
    ) -> None:
        """Handles labels being added to a message.

        Args:
            message (Dict[str, Any]): A dictionary representing the message.
            label_ids (List[str]): A list of label IDs that were added.

        """
        try:
            email = Email.objects.get(gmail_id=message["id"])
            current_labels = set(email.labels or [])
            new_labels = set(label_ids)

            if new_labels - current_labels:
                email.labels = list(current_labels | new_labels)
                email.history_id = self._current_history_id
                email.last_sync_at = timezone.now()
                email.save()

                for label_id in new_labels - current_labels:
                    EmailLabelHistory.objects.create(
                        email=email,
                        label_id=label_id,
                        action="added",
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

    def _handle_label_removed(
        self,
        message: dict[str, Any],
        label_ids: list[str],
    ) -> None:
        """Handles labels being removed from a message.

        Args:
            message (Dict[str, Any]): A dictionary representing the message.
            label_ids (List[str]): A list of label IDs that were removed.

        """
        try:
            email = Email.objects.get(gmail_id=message["id"])
            current_labels = set(email.labels or [])
            removed_labels = set(label_ids)

            if removed_labels & current_labels:
                email.labels = list(current_labels - removed_labels)
                email.history_id = self._current_history_id
                email.last_sync_at = timezone.now()
                email.save()

                for label_id in removed_labels & current_labels:
                    EmailLabelHistory.objects.create(
                        email=email,
                        label_id=label_id,
                        action="removed",
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
