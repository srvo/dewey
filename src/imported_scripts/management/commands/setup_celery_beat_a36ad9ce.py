"""Command to set up Celery Beat schedule."""

from typing import Any

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


def _get_or_create_interval_schedule(every: int, period: str) -> IntervalSchedule:
    """Gets or creates an IntervalSchedule.

    Args:
    ----
        every: The frequency of the schedule.
        period: The period of the schedule (e.g., 'minutes', 'seconds').

    Returns:
    -------
        The IntervalSchedule object.

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
    """Creates or updates a PeriodicTask.

    Args:
    ----
        name: The name of the task.
        task: The Celery task to run.
        interval: The IntervalSchedule for the task.
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
    """Set up Celery Beat schedule in database."""

    help = "Set up Celery Beat schedule in database"

    def handle(self, *args: Any, **options: Any) -> None:
        """Handles the command execution.

        Args:
        ----
            *args: Additional arguments.
            **options: Additional options.

        """
        fifteen_minutes_schedule = _get_or_create_interval_schedule(
            every=15,
            period=IntervalSchedule.MINUTES,
        )
        thirty_minutes_schedule = _get_or_create_interval_schedule(
            every=30,
            period=IntervalSchedule.MINUTES,
        )

        _create_or_update_periodic_task(
            name="Sync Gmail History",
            task="sync_gmail_history_task",
            interval=fifteen_minutes_schedule,
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

        self.stdout.write(
            self.style.SUCCESS("Periodic tasks have been set up successfully!"),
        )
