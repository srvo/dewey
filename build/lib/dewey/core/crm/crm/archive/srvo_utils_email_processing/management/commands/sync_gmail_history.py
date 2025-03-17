"""Management command to sync Gmail history."""

import structlog
from django.core.management.base import BaseCommand
from email_processing.gmail_history_sync import full_sync_gmail
from database.models import Email, EventLog
from googleapiclient.discovery import build

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    """Command to sync Gmail history."""

    help = "Sync Gmail history for new or updated messages"

    def handle(self, *args, **options):
        """Execute the command."""
        try:
            # Check if we have any emails
            has_emails = Email.objects.exists()

            if not has_emails:
                # Perform full sync
                self.stdout.write("Starting full sync...")
                logger.info("starting_full_sync")
                success, messages_synced = full_sync_gmail()

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Full sync completed. Synced {messages_synced} messages."
                        )
                    )
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
                else:
                    self.stdout.write(self.style.ERROR("Full sync failed."))
                    logger.error("full_sync_failed")
                    return

            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Emails already exist. Use the Celery task for incremental sync."
                    )
                )
                logger.info("emails_exist_use_celery")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during sync: {str(e)}"))
            logger.error(
                "sync_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            EventLog.objects.create(
                event_type="SYNC_ERROR",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                performed_by="system",
            )


def get_gmail_service():
    """Initialize and return the Gmail service client."""
    credentials = get_gmail_credentials()
    service = build("gmail", "v1", credentials=credentials)
    return service
