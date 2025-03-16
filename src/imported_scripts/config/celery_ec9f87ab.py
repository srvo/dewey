"""Celery configuration."""

import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("srvo_utils")

# Namespace configuration keys with 'CELERY_'
app.config_from_object("django.conf:settings", namespace="CELERY")

# Configure Celery
app.conf.update(
    broker_connection_retry_on_startup=True,  # New recommended setting
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Prevent worker starvation
    task_acks_late=True,  # Ensure tasks are only acknowledged after completion
    task_reject_on_worker_lost=True,  # Requeue tasks if worker is killed
    task_queues={
        "gmail_sync": {
            "exchange": "gmail_sync",
            "routing_key": "gmail.sync",
        },
        "contact_enrichment": {
            "exchange": "contact_enrichment",
            "routing_key": "contact.enrichment",
        },
    },
    task_default_queue="gmail_sync",  # Default queue for tasks
    task_routes={
        "sync_gmail_history_task": {"queue": "gmail_sync"},
        "enrich_contacts_task": {"queue": "contact_enrichment"},
    },
)

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")


app.conf.beat_schedule = {
    "sync_gmail_history": {
        "task": "sync_gmail_history_task",
        "schedule": 300.0,  # Every 5 minutes
    },
    "enrich_contacts": {
        "task": "enrich_contacts_task",
        "schedule": 3600.0,  # Every hour
    },
    "backfill_email_metadata": {
        "task": "backfill_email_metadata_task",
        "schedule": 1800.0,  # Every 30 minutes
    },
}
