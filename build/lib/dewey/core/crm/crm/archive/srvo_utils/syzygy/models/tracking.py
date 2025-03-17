"""Models for tracking LLM and tool usage."""

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator


class LLMTransaction(models.Model):
    """Tracks all LLM interactions."""

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
    model_name = models.CharField(max_length=255)
    prompt = models.TextField()
    response = models.TextField(null=True, blank=True)
    input_tokens = models.IntegerField(validators=[MinValueValidator(0)])
    output_tokens = models.IntegerField(validators=[MinValueValidator(0)])
    cost = models.DecimalField(max_digits=10, decimal_places=6)
    latency_ms = models.IntegerField(validators=[MinValueValidator(0)])
    metadata = JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "LLM Transaction"
        verbose_name_plural = "LLM Transactions"

    def __str__(self):
        return f"{self.model_name} - {self.created_at}"


class ToolUsage(models.Model):
    """Tracks usage of automated tools."""

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
    tool_name = models.CharField(max_length=255)
    parameters = JSONField(default=dict)
    result = JSONField(null=True, blank=True)
    duration_ms = models.IntegerField(validators=[MinValueValidator(0)])
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    resource_usage = JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tool Usage"
        verbose_name_plural = "Tool Usage"

    def __str__(self):
        return f"{self.tool_name} - {self.created_at}"
