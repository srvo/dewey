from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Sets up periodic tasks for email syncing and contact enrichment"

    def handle(self, *args, **options) -> None:
        # Create schedules if they don't exist
        five_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )

        fifteen_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=15,
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
                "start_time": timezone.now(),
            },
        )

        # Set up contact enrichment task (every 15 minutes)
        PeriodicTask.objects.update_or_create(
            name="Enrich Contacts",
            defaults={
                "task": "enrich_contacts_task",
                "interval": fifteen_minutes_schedule,
                "enabled": True,
                "description": "Enriches contact information with interaction data",
                "start_time": timezone.now(),
                "kwargs": '{"batch_size": 50}',
            },
        )

        self.stdout.write(
            self.style.SUCCESS("Periodic tasks have been set up successfully!"),
        )
