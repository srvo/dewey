"""Models for timeline view components."""

import uuid

from django.db import models
from django.utils import timezone

from .research import Universe


class TimelineView(models.Model):
    """Database view for unified timeline with enhanced tracking."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=50, default="unknown", db_index=True)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    description = models.TextField(default="", blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    source_system = models.CharField(max_length=50, default="syzygy", db_index=True)
    importance_level = models.IntegerField(
        default=0,
        help_text="0=normal, 1=important, 2=critical",
    )
    related_objects = models.JSONField(
        default=list,
        help_text="List of related object IDs in format [{'type': 'contact', 'id': 123}]",
    )

    class Meta:
        managed = False  # This tells Django this is a database view
        db_table = "timeline_view"
        indexes = [
            models.Index(fields=["created_at"], name="timeline_created_at_idx"),
            models.Index(
                fields=["event_type", "created_at"],
                name="timeline_type_date_idx",
            ),
            models.Index(
                fields=["user_id", "created_at"],
                name="timeline_user_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.created_at}"


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Client(models.Model):
    """Client information for timeline tracking."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    organization = models.CharField(max_length=255, null=True, blank=True)
    preferences = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients"
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        indexes = [
            models.Index(fields=["email"], name="client_email_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Transcript(models.Model):
    """Transcript of client interactions."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.CASCADE)
    security = models.ForeignKey(
        Universe,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    interaction_type = models.CharField(max_length=50, default="general")
    content = models.TextField(default="")
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "transcripts"
        verbose_name = "Transcript"
        verbose_name_plural = "Transcripts"
        indexes = [
            models.Index(fields=["client"], name="transcript_client_idx"),
            models.Index(fields=["security"], name="transcript_security_idx"),
            models.Index(fields=["created_at"], name="transcript_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.client.name if self.client else 'No Client'} - {self.interaction_type} ({self.created_at})"


class TranscriptAnalysis(models.Model):
    """Analysis of client interaction transcripts."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    transcript = models.OneToOneField(
        Transcript,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    summary = models.TextField(default="")
    key_points = models.JSONField(default=list)
    sentiment = models.FloatField(default=0.0)
    topics = models.JSONField(default=list)
    entities = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transcript_analyses"
        verbose_name = "Transcript Analysis"
        verbose_name_plural = "Transcript Analyses"
        indexes = [
            models.Index(fields=["transcript"], name="analysis_transcript_idx"),
        ]

    def __str__(self) -> str:
        return f"Analysis of {self.transcript or 'Unassigned Transcript'}"


class Activity(models.Model):
    """Timeline activity tracking."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, default="general")
    description = models.TextField(default="")
    related_security = models.ForeignKey(
        Universe,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "activities"
        verbose_name = "Activity"
        verbose_name_plural = "Activities"
        indexes = [
            models.Index(fields=["client"], name="activity_client_idx"),
            models.Index(fields=["activity_type"], name="activity_type_idx"),
            models.Index(fields=["created_at"], name="activity_date_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.client.name if self.client else 'No Client'} - {self.activity_type}"
        )
