from django.conf import settings
from django.db import models


class EventLog(models.Model):
    EVENT_TYPES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
    )

    event_type = models.CharField(max_length=10, choices=EVENT_TYPES)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="event_logs",
    )

    def __str__(self) -> str:
        return f"{self.event_type} event by {self.created_by} at {self.created_at}"

    class Meta:
        db_table = "logs_event_logs"
