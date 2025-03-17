"""Models for email triage and response management."""

from django.db import models
from django.utils import timezone
from markdownx.models import MarkdownxField
import uuid

from .timeline import Client


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class ResponseDraft(models.Model):
    """Draft responses to client emails."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.CASCADE)
    original_email = models.TextField(default="")
    email_subject = models.CharField(max_length=255, default="")
    draft_content = MarkdownxField(
        default="",
        help_text="Write your response in Markdown format. You can use the preview panel to see how it will look.",
    )
    status = models.CharField(max_length=50, default="draft")
    priority = models.IntegerField(default=0)
    context_notes = MarkdownxField(
        blank=True,
        default="",
        help_text="Additional context or notes about this response in Markdown format.",
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.CharField(max_length=255, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "response_drafts"
        verbose_name = "Response Draft"
        verbose_name_plural = "Response Drafts"
        indexes = [
            models.Index(fields=["client"], name="draft_client_idx"),
            models.Index(fields=["status"], name="draft_status_idx"),
            models.Index(fields=["priority"], name="draft_priority_idx"),
            models.Index(fields=["created_at"], name="draft_created_idx"),
        ]

    def __str__(self):
        return (
            f"{self.client.name if self.client else 'No Client'} - {self.email_subject}"
        )


class ProcessingMetrics(models.Model):
    """Metrics for email processing and response generation."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    response_draft = models.OneToOneField(
        ResponseDraft, null=True, blank=True, on_delete=models.CASCADE
    )
    processing_time_ms = models.IntegerField(default=0)
    confidence_score = models.FloatField(default=0.0)
    complexity_score = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(default=0.0)
    topic_scores = models.JSONField(default=dict)
    model_metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "processing_metrics"
        verbose_name = "Processing Metric"
        verbose_name_plural = "Processing Metrics"
        indexes = [
            models.Index(fields=["response_draft"], name="metrics_draft_idx"),
            models.Index(
                fields=["confidence_score", "complexity_score"],
                name="metrics_scores_idx",
            ),
        ]

    def __str__(self):
        return f"Metrics for {self.response_draft or 'Unassigned Draft'}"
