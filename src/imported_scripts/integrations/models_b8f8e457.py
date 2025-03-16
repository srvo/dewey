from django.db import models
from django.utils import timezone


class GoogleIntegration(models.Model):
    credentials = models.JSONField()
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    last_sync = models.DateTimeField(auto_now=True)

    # Scopes tracking
    calendar_enabled = models.BooleanField(default=False)
    contacts_enabled = models.BooleanField(default=False)
    drive_enabled = models.BooleanField(default=False)
    gmail_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Google Integration"


class GoogleCalendarEvent(models.Model):
    integration = models.ForeignKey(GoogleIntegration, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=255, unique=True)
    summary = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    calendar_id = models.CharField(max_length=255)
    last_synced = models.DateTimeField(default=timezone.now)


class GoogleContact(models.Model):
    integration = models.ForeignKey(GoogleIntegration, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=255, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    last_synced = models.DateTimeField(default=timezone.now)


class GoogleDocument(models.Model):
    integration = models.ForeignKey(GoogleIntegration, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=500)
    doc_type = models.CharField(max_length=20)  # 'sheet', 'doc', etc.
    last_modified = models.DateTimeField()
    last_synced = models.DateTimeField(default=timezone.now)


class GmailMessage(models.Model):
    integration = models.ForeignKey(GoogleIntegration, on_delete=models.CASCADE)
    message_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255)
    subject = models.CharField(max_length=500)
    sender = models.EmailField()
    recipient = models.EmailField()
    date = models.DateTimeField()
    snippet = models.TextField()  # Preview of the message
    labels = models.JSONField(default=list)
    last_synced = models.DateTimeField(default=timezone.now)


class SyncLog(models.Model):
    integration = models.ForeignKey(GoogleIntegration, on_delete=models.CASCADE)
    service = models.CharField(
        max_length=20,
        choices=[
            ("calendar", "Calendar"),
            ("contacts", "Contacts"),
            ("drive", "Drive"),
            ("gmail", "Gmail"),
        ],
    )
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
