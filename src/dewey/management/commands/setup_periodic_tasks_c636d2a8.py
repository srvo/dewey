# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Management command to set up periodic tasks."""

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Sets up periodic tasks for email syncing and contact enrichment"

    def handle(self, *args, **options) -> None:
        # Create schedules if they don't exist
        five_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )

        thirty_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.MINUTES,
        )

        sixty_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=60,
            period=IntervalSchedule.MINUTES,
        )

        # Set up Gmail history sync task (every 5 minutes)
        PeriodicTask.objects.update_or_create(
            name="Sync Gmail History",
            defaults={
                "task": "sync_gmail_history_task",
                "interval": five_minutes_schedule,
                "enabled": True,
                "description": "Syncs Gmail history to get new emails and updates",
                "queue": "gmail_sync",
                "routing_key": "gmail.sync",
            },
        )

        # Set up metadata backfill task (every 30 minutes)
        PeriodicTask.objects.update_or_create(
            name="Backfill Email Metadata",
            defaults={
                "task": "backfill_email_metadata_task",
                "interval": thirty_minutes_schedule,
                "enabled": True,
                "description": "Backfills missing metadata for emails",
                "queue": "gmail_sync",
                "routing_key": "gmail.sync",
            },
        )

        # Set up contact enrichment task (every hour)
        PeriodicTask.objects.update_or_create(
            name="Enrich Contacts",
            defaults={
                "task": "enrich_contacts_task",
                "interval": sixty_minutes_schedule,
                "enabled": True,
                "description": "Enriches contact information with interaction data",
                "queue": "contact_enrichment",
                "routing_key": "contact.enrichment",
            },
        )

        self.stdout.write(
            self.style.SUCCESS("Periodic tasks have been set up successfully!"),
        )
