import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ethical_capital.settings.base")

app = Celery("ethical_capital")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
