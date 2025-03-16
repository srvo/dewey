"""Base models for Syzygy application."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TimelineEvent(models.Model):
    """Base model for timeline events with tight constraints."""

    created_at = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(
        max_length=50,
        choices=[
            ("llm", "LLM Interaction"),
            ("tool", "Tool Usage"),
            ("email", "Email Processing"),
            ("contact", "Contact Update"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="user_id",
    )
    metadata = models.JSONField(default=dict)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_at", "event_type", "user_id"],
                name="unique_timeline_event",
            ),
        ]


class LLMTransaction(TimelineEvent):
    """Track LLM interactions with tight constraints."""

    model_name = models.CharField(max_length=100, db_index=True)
    prompt = models.TextField()
    response = models.TextField()
    input_tokens = models.IntegerField(validators=[MinValueValidator(0)])
    output_tokens = models.IntegerField(validators=[MinValueValidator(0)])
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        validators=[MinValueValidator(0)],
    )
    latency_ms = models.IntegerField(validators=[MinValueValidator(0)])

    class Meta(TimelineEvent.Meta):
        constraints = [
            *TimelineEvent.Meta.constraints,
            models.CheckConstraint(
                check=models.Q(input_tokens__gte=0),
                name="input_tokens_positive",
            ),
            models.CheckConstraint(
                check=models.Q(output_tokens__gte=0),
                name="output_tokens_positive",
            ),
            models.CheckConstraint(check=models.Q(cost__gte=0), name="cost_positive"),
            models.CheckConstraint(
                check=models.Q(latency_ms__gte=0),
                name="latency_positive",
            ),
        ]


class ToolUsage(TimelineEvent):
    """Track automated tool usage with tight constraints."""

    tool_name = models.CharField(max_length=100, db_index=True)
    parameters = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    duration_ms = models.IntegerField(validators=[MinValueValidator(0)])
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    resource_usage = models.JSONField(default=dict)

    class Meta(TimelineEvent.Meta):
        constraints = [
            *TimelineEvent.Meta.constraints,
            models.CheckConstraint(
                check=models.Q(duration_ms__gte=0),
                name="duration_positive",
            ),
        ]
