from celery import Celery

from config import CELERY_CONFIG  # Use existing config

from .file_analyzer import scan_storage

app = Celery("data_processor")
app.config_from_object(CELERY_CONFIG)


# Add to existing tasks
@app.task(bind=True, max_retries=3)
def analyze_files(self) -> None:
    try:
        scan_storage()
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


# Schedule the task
app.conf.beat_schedule = {
    "analyze-files-nightly": {
        "task": "tasks.analyze_files",
        "schedule": crontab(hour=3, minute=0),  # 3 AM
    },
}
