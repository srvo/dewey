"""Database models for contact enrichment system."""

from django.db import models


class Contact(models.Model):
    """Represents a contact extracted from email communications."""

    id = models.CharField(max_length=26, primary_key=True)  # ULID
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=50, default="individual")
    enrichment_status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    )
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contacts"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["category"]),
            models.Index(fields=["enrichment_status"]),
        ]

    def __str__(self):
        return f"Contact(id={self.id}, email={self.email})"


class EnrichmentTask(models.Model):
    """Tracks enrichment tasks and their status."""

    id = models.CharField(max_length=26, primary_key=True)  # ULID
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=26)  # ULID
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="pending")
    attempts = models.IntegerField(default=0)
    metadata = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "enrichment_tasks"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["task_type", "status"]),
        ]

    def __str__(self):
        return (
            f"EnrichmentTask(id={self.id}, type={self.task_type}, status={self.status})"
        )


class EnrichmentSource(models.Model):
    """Stores enrichment data from various sources with version control."""

    id = models.CharField(max_length=26, primary_key=True)  # ULID
    source_type = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=26)  # ULID
    data = models.JSONField()
    confidence = models.FloatField()
    valid_from = models.DateTimeField(auto_now_add=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "enrichment_sources"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["source_type", "valid_to"]),
        ]

    def __str__(self):
        return f"EnrichmentSource(id={self.id}, type={self.source_type}, entity={self.entity_id})"
