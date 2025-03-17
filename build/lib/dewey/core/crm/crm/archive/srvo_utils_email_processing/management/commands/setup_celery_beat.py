"""Command to set up Celery Beat schedule."""

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from django.utils import timezone
import json


class Command(BaseCommand):
    """Set up Celery Beat schedule in database."""

    help = "Set up Celery Beat schedule in database"

    def handle(self, *args, **options):
        # Create schedules if they don't exist
        fifteen_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=15,
            period=IntervalSchedule.MINUTES,
        )

        thirty_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.MINUTES,
        )

        # Set up Gmail history sync task (every 15 minutes)
        PeriodicTask.objects.update_or_create(
            name="Sync Gmail History",
            defaults={
                "task": "sync_gmail_history_task",
                "interval": fifteen_minutes_schedule,
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

        self.stdout.write(
            self.style.SUCCESS("Periodic tasks have been set up successfully!")
        )
