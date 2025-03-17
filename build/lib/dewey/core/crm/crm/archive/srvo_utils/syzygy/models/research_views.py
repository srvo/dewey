"""Models for research view components."""

from django.db import models
from django.utils import timezone
import uuid

from .research import Universe


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class MentalModel(models.Model):
    """Framework for understanding a company or industry."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    name = models.CharField(max_length=255, default="")
    description = models.TextField(default="")
    key_components = models.JSONField(default=dict)
    relationships = models.JSONField(default=dict)
    security = models.ForeignKey(
        Universe, null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mental_models"
        verbose_name = "Mental Model"
        verbose_name_plural = "Mental Models"
        indexes = [
            models.Index(fields=["security"], name="mental_model_security_idx"),
        ]

    def __str__(self):
        return (
            f"{self.security.ticker if self.security else 'No Security'} - {self.name}"
        )


class KnowledgeReference(models.Model):
    """Key pieces of knowledge about a security."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    security = models.ForeignKey(
        Universe, null=True, blank=True, on_delete=models.CASCADE
    )
    mental_model = models.ForeignKey(
        MentalModel, null=True, blank=True, on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255, default="")
    content = models.TextField(default="")
    source_url = models.URLField(max_length=2048, null=True, blank=True)
    source_type = models.CharField(max_length=50, default="general")
    confidence = models.IntegerField(default=0)
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_references"
        verbose_name = "Knowledge Reference"
        verbose_name_plural = "Knowledge References"
        indexes = [
            models.Index(fields=["security"], name="knowledge_security_idx"),
            models.Index(fields=["mental_model"], name="knowledge_model_idx"),
        ]

    def __str__(self):
        return (
            f"{self.security.ticker if self.security else 'No Security'} - {self.title}"
        )


class ContentReference(models.Model):
    """Reference to specific content used in research."""

    id = models.CharField(max_length=26, primary_key=True, default=generate_uuid)
    security = models.ForeignKey(
        Universe, null=True, blank=True, on_delete=models.CASCADE
    )
    knowledge_ref = models.ForeignKey(
        KnowledgeReference, null=True, blank=True, on_delete=models.CASCADE
    )
    content_type = models.CharField(max_length=50, default="general")
    content_id = models.CharField(max_length=26, default=generate_uuid)
    relevance_score = models.FloatField(default=0.0)
    context = models.TextField(default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "content_references"
        verbose_name = "Content Reference"
        verbose_name_plural = "Content References"
        indexes = [
            models.Index(fields=["security"], name="content_security_idx"),
            models.Index(fields=["knowledge_ref"], name="content_knowledge_idx"),
            models.Index(
                fields=["content_type", "content_id"], name="content_type_id_idx"
            ),
        ]

    def __str__(self):
        return f"{self.security.ticker if self.security else 'No Security'} - {self.content_type} Reference"
