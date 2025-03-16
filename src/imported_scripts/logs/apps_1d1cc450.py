from pathlib import Path

from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logs"
    path = str(Path(__file__).resolve().parent)
