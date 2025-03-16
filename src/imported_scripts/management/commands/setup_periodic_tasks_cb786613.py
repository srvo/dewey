"""Management command to set up periodic tasks."""

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


def _create_interval_schedule(every: int, period: str) -> IntervalSchedule:
    """Creates an interval schedule if it doesn't exist.

    Args:
    ----
        every: The frequency of the schedule.
        period: The period of the schedule (e.g., 'minutes', 'seconds').

    Returns:
    -------
        The created or existing IntervalSchedule object.

    """
    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=every,
        period=period,
    )
    return schedule


def _create_or_update_periodic_task(
    name: str,
    task: str,
    interval: IntervalSchedule,
    description: str,
    queue: str,
    routing_key: str,
) -> None:
    """Creates or updates a periodic task.

    Args:
    ----
        name: The name of the periodic task.
        task: The Celery task to execute.
        interval: The interval schedule for the task.
        description: A description of the task.
        queue: The Celery queue to use.
        routing_key: The Celery routing key to use.

    """
    PeriodicTask.objects.update_or_create(
        name=name,
        defaults={
            "task": task,
            "interval": interval,
            "enabled": True,
            "description": description,
            "queue": queue,
            "routing_key": routing_key,
        },
    )


class Command(BaseCommand):
    """Sets up periodic tasks for email syncing and contact enrichment."""

    help = "Sets up periodic tasks for email syncing and contact enrichment"

    def handle(self, *args, **options) -> None:
        """Handles the creation and setup of periodic tasks.

        Args:
        ----
            *args: Additional arguments.
            **options: Additional options.

        """
        five_minutes_schedule = _create_interval_schedule(5, IntervalSchedule.MINUTES)
        thirty_minutes_schedule = _create_interval_schedule(
            30,
            IntervalSchedule.MINUTES,
        )
        sixty_minutes_schedule = _create_interval_schedule(60, IntervalSchedule.MINUTES)

        _create_or_update_periodic_task(
            name="Sync Gmail History",
            task="sync_gmail_history_task",
            interval=five_minutes_schedule,
            description="Syncs Gmail history to get new emails and updates",
            queue="gmail_sync",
            routing_key="gmail.sync",
        )

        _create_or_update_periodic_task(
            name="Backfill Email Metadata",
            task="backfill_email_metadata_task",
            interval=thirty_minutes_schedule,
            description="Backfills missing metadata for emails",
            queue="gmail_sync",
            routing_key="gmail.sync",
        )

        _create_or_update_periodic_task(
            name="Enrich Contacts",
            task="enrich_contacts_task",
            interval=sixty_minutes_schedule,
            description="Enriches contact information with interaction data",
            queue="contact_enrichment",
            routing_key="contact.enrichment",
        )

        self.stdout.write(
            self.style.SUCCESS("Periodic tasks have been set up successfully!"),
        )
