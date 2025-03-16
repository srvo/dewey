from django.db import models


class Contact(models.Model):
    """Represents a contact extracted from email communications."""

    id: str = models.CharField(max_length=26, primary_key=True)  # ULID
    email: str = models.EmailField(unique=True)
    name: str = models.CharField(max_length=255, null=True, blank=True)
    category: str = models.CharField(max_length=50, default="individual")
    enrichment_status: str = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    )
    metadata: dict = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta data for Contact model."""

        db_table = "contacts"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["category"]),
            models.Index(fields=["enrichment_status"]),
        ]

    def __str__(self) -> str:
        """Returns a string representation of the Contact object."""
        return f"Contact(id={self.id}, email={self.email})"


class EnrichmentTask(models.Model):
    """Tracks enrichment tasks and their status."""

    id: str = models.CharField(max_length=26, primary_key=True)  # ULID
    entity_type: str = models.CharField(max_length=50)
    entity_id: str = models.CharField(max_length=26)  # ULID
    task_type: str = models.CharField(max_length=50)
    status: str = models.CharField(max_length=20, default="pending")
    attempts: int = models.IntegerField(default=0)
    metadata: dict = models.JSONField(null=True, blank=True)
    result: dict = models.JSONField(null=True, blank=True)
    error_message: str = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta data for EnrichmentTask model."""

        db_table = "enrichment_tasks"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["task_type", "status"]),
        ]

    def __str__(self) -> str:
        """Returns a string representation of the EnrichmentTask object."""
        return (
            "EnrichmentTask("
            f"id={self.id}, type={self.task_type}, status={self.status})"
        )


class EnrichmentSource(models.Model):
    """Stores enrichment data from various sources with version control."""

    id: str = models.CharField(max_length=26, primary_key=True)  # ULID
    source_type: str = models.CharField(max_length=50)
    entity_type: str = models.CharField(max_length=50)
    entity_id: str = models.CharField(max_length=26)  # ULID
    data: dict = models.JSONField()
    confidence: float = models.FloatField()
    valid_from = models.DateTimeField(auto_now_add=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta data for EnrichmentSource model."""

        db_table = "enrichment_sources"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["source_type", "valid_to"]),
        ]

    def __str__(self) -> str:
        """Returns a string representation of the EnrichmentSource object."""
        return (
            "EnrichmentSource("
            f"id={self.id}, type={self.source_type}, entity={self.entity_id})"
        )
