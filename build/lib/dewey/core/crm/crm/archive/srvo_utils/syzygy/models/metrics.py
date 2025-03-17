"""Models for tracking AI agent interactions and metrics."""

from django.db import models
import django.utils.timezone


class AgentInteraction(models.Model):
    """Records metrics for interactions with AI agents."""

    id = models.CharField(max_length=26, primary_key=True)
    agent_type = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)
    operation = models.CharField(max_length=100)

    # Token metrics
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()

    # Performance metrics
    latency_ms = models.IntegerField()
    success = models.BooleanField()
    error_type = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    # Cost tracking
    cost_millicents = models.IntegerField()

    # Entity context
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=26)

    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=django.utils.timezone.now)

    class Meta:
        db_table = "agent_interactions"
        indexes = [
            models.Index(fields=["agent_type"], name="interaction_agent_idx"),
            models.Index(fields=["model_name"], name="interaction_model_idx"),
            models.Index(fields=["created_at"], name="interaction_created_idx"),
        ]

    def __str__(self):
        return f"{self.agent_type} - {self.operation} ({self.created_at})"
