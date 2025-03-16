"""Management command to sync Gmail history."""

import structlog
from database.models import Email, EventLog
from django.core.management.base import BaseCommand
from email_processing.gmail_history_sync import full_sync_gmail

logger = structlog.get_logger(__name__)


def log_sync_completion(messages_synced: int) -> None:
    """Logs the completion of a successful full sync.

    Args:
    ----
        messages_synced: The number of messages synced during the full sync.

    """
    logger.info(
        "full_sync_completed",
        messages_synced=messages_synced,
    )
    EventLog.objects.create(
        event_type="FULL_SYNC_COMPLETED",
        details={
            "messages_synced": messages_synced,
        },
        performed_by="system",
    )


def log_sync_error(error: Exception) -> None:
    """Logs an error that occurred during the sync process.

    Args:
    ----
        error: The exception that was raised.

    """
    logger.error(
        "sync_error",
        error=str(error),
        error_type=type(error).__name__,
    )
    EventLog.objects.create(
        event_type="SYNC_ERROR",
        details={
            "error": str(error),
            "error_type": type(error).__name__,
        },
        performed_by="system",
    )


class Command(BaseCommand):
    """Command to sync Gmail history."""

    help = "Sync Gmail history for new or updated messages"

    def handle(self, *args, **options) -> None:
        """Executes the command to sync Gmail history."""
        try:
            if not Email.objects.exists():
                self._perform_full_sync()
            else:
                self._warn_existing_emails()

        except Exception as e:
            self._handle_exception(e)

    def _perform_full_sync(self) -> None:
        """Performs a full sync of Gmail history."""
        self.stdout.write("Starting full sync...")
        logger.info("starting_full_sync")
        success, messages_synced = full_sync_gmail()

        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Full sync completed. Synced {messages_synced} messages.",
                ),
            )
            log_sync_completion(messages_synced)
        else:
            self.stdout.write(self.style.ERROR("Full sync failed."))
            logger.error("full_sync_failed")

    def _warn_existing_emails(self) -> None:
        """Warns the user that emails already exist and suggests using Celery."""
        self.stdout.write(
            self.style.WARNING(
                "Emails already exist. Use the Celery task for incremental sync.",
            ),
        )
        logger.info("emails_exist_use_celery")

    def _handle_exception(self, e: Exception) -> None:
        """Handles exceptions that occur during the sync process.

        Args:
        ----
            e: The exception that was raised.

        """
        self.stdout.write(self.style.ERROR(f"Error during sync: {e!s}"))
        log_sync_error(e)
