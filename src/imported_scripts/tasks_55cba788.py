"""Celery tasks for email processing."""

import sentry_sdk
import structlog
from celery import shared_task
from database.models import Contact, Email, EnrichmentTask, EventLog
from django.db import models
from django.utils import timezone

from .contact_enrichment import ContactEnrichmentService
from .email_enrichment import EmailEnrichmentService
from .gmail_history_sync import full_sync_gmail, sync_gmail_history

logger = structlog.get_logger(__name__)


@shared_task(
    name="sync_gmail_history_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,  # Max 1 hour delay between retries
    retry_jitter=True,  # Add randomness to retry delays
)
def sync_gmail_history_task(self) -> None:
    """Task to sync Gmail history.
    This task will:
    1. Check if any emails exist in the database
    2. If no emails, perform a full sync
    3. If emails exist, perform an incremental sync from the last history ID
    4. Handle errors gracefully with thresholds.
    """
    try:
        # Set task context in Sentry
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("task", "sync_gmail_history")
            scope.set_tag("retry_count", self.request.retries)
            scope.set_context(
                "task_info",
                {
                    "task_id": self.request.id,
                    "retries": self.request.retries,
                    "max_retries": self.max_retries,
                },
            )

        # Check if we have any emails
        has_emails = Email.objects.exists()

        if not has_emails:
            # Perform full sync
            logger.info("starting_full_sync")
            success, messages_synced = full_sync_gmail()

            if success:
                logger.info(
                    "full_sync_completed",
                    messages_synced=messages_synced,
                )
                EventLog.objects.create(
                    event_type="FULL_SYNC_COMPLETED",
                    details={
                        "messages_synced": messages_synced,
                    },
                    performed_by="celery",
                )
            else:
                logger.error("full_sync_failed_with_errors")
                # Track sync failure in Sentry
                sentry_sdk.capture_message(
                    "Full sync failed with errors",
                    level="error",
                    extras={
                        "messages_synced": messages_synced,
                    },
                )
                return

        else:
            # Perform incremental sync
            latest_email = Email.objects.order_by("-last_sync_at").first()
            start_history_id = latest_email.history_id if latest_email else None

            success, messages_updated, pages_processed = sync_gmail_history(
                start_history_id,
            )

            if success:
                logger.info(
                    "incremental_sync_completed",
                    messages_updated=messages_updated,
                    pages_processed=pages_processed,
                )
                EventLog.objects.create(
                    event_type="INCREMENTAL_SYNC_COMPLETED",
                    details={
                        "messages_updated": messages_updated,
                        "pages_processed": pages_processed,
                        "start_history_id": start_history_id,
                    },
                    performed_by="celery",
                )
            else:
                logger.error(
                    "incremental_sync_failed_with_errors",
                    start_history_id=start_history_id,
                )
                # Track sync failure in Sentry
                sentry_sdk.capture_message(
                    "Incremental sync failed with errors",
                    level="error",
                    extras={
                        "start_history_id": start_history_id,
                        "messages_updated": messages_updated,
                        "pages_processed": pages_processed,
                    },
                )
                return

    except Exception as e:
        logger.exception(
            "gmail_sync_error",
            error=str(e),
            error_type=type(e).__name__,
            sync_type="full" if not Email.objects.exists() else "incremental",
        )
        # Track error in Sentry
        sentry_sdk.capture_exception(e)
        EventLog.objects.create(
            event_type="SYNC_ERROR",
            details={
                "error": str(e),
                "error_type": type(e).__name__,
                "sync_type": "full" if not Email.objects.exists() else "incremental",
                "start_history_id": (
                    start_history_id if "start_history_id" in locals() else None
                ),
                "retry_count": self.request.retries,
            },
            performed_by="celery",
        )
        # Let Celery's autoretry handle the retry with exponential backoff
        raise


@shared_task(
    name="enrich_contacts_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def enrich_contacts_task(self, batch_size: int = 50) -> None:
    """Task to enrich contact information.
    This task will:
    1. Get contacts that haven't been enriched recently
    2. Process them in batches
    3. Update their information with interaction data.

    Args:
    ----
        batch_size: Number of contacts to process in each batch

    """
    try:
        # Get contacts to process
        contacts = Contact.objects.filter(
            last_interaction__isnull=True,  # Never processed
        ).order_by("created_at")[:batch_size]

        if not contacts:
            # If no new contacts, get ones that haven't been updated in a while
            contacts = Contact.objects.filter(
                updated_at__lt=timezone.now() - timezone.timedelta(days=1),
            ).order_by("updated_at")[:batch_size]

        if not contacts:
            logger.info("no_contacts_to_enrich")
            return

        # Initialize service
        enrichment_service = ContactEnrichmentService()

        # Process contacts
        processed_count = 0
        error_count = 0

        for contact in contacts:
            try:
                # Create enrichment task
                enrichment_task = EnrichmentTask.objects.create(
                    entity_type="contact",
                    entity_id=contact.id,
                    task_type="contact_info",
                    created_by="celery",
                    updated_by="celery",
                    status="in_progress",
                )

                success = enrichment_service.enrich_contact(contact, enrichment_task)
                if success:
                    processed_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                logger.exception(
                    "contact_enrichment_failed",
                    contact_id=contact.id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                if "enrichment_task" in locals():
                    enrichment_task.mark_failed(str(e))

        logger.info(
            "contact_enrichment_batch_completed",
            total_contacts=len(contacts),
            processed_count=processed_count,
            error_count=error_count,
        )

        # Create event log
        EventLog.objects.create(
            event_type="CONTACT_ENRICHMENT_COMPLETED",
            details={
                "total_contacts": len(contacts),
                "processed_count": processed_count,
                "error_count": error_count,
                "batch_size": batch_size,
            },
        )

    except Exception as e:
        logger.exception(
            "contact_enrichment_task_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Create error event
        EventLog.objects.create(
            event_type="CONTACT_ENRICHMENT_ERROR",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise self.retry(exc=e)


@shared_task(
    name="backfill_email_metadata_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
)
def backfill_email_metadata_task(self):
    """Task to backfill email metadata for emails missing message bodies.
    This will:
    1. Find emails with missing message bodies
    2. Fetch full message data from Gmail
    3. Update the email records with decoded message bodies.
    """
    try:
        # Set task context in Sentry
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("task", "backfill_email_metadata")
            scope.set_tag("retry_count", self.request.retries)
            scope.set_context(
                "task_info",
                {
                    "task_id": self.request.id,
                    "retries": self.request.retries,
                    "max_retries": self.max_retries,
                },
            )

        enrichment_service = EmailEnrichmentService()
        total_processed = 0
        total_updated = 0

        # Find emails missing message bodies
        emails_to_update = Email.objects.filter(
            models.Q(plain_body="") | models.Q(plain_body__isnull=True),
            models.Q(html_body="") | models.Q(html_body__isnull=True),
        ).order_by("-received_at")[
            :100
        ]  # Process in batches of 100

        for email in emails_to_update:
            try:
                if enrichment_service.enrich_email(email):
                    total_updated += 1
                total_processed += 1

            except Exception as e:
                logger.exception(
                    "backfill_error",
                    gmail_id=email.gmail_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                EventLog.objects.create(
                    event_type="BACKFILL_ERROR",
                    email=email,
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        logger.info(
            "backfill_completed",
            total_processed=total_processed,
            total_updated=total_updated,
        )

        return {
            "total_processed": total_processed,
            "total_updated": total_updated,
            "status": "completed",
        }

    except Exception as e:
        logger.exception("backfill_failed", error=str(e), error_type=type(e).__name__)
        EventLog.objects.create(
            event_type="BACKFILL_ERROR",
            details={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise
