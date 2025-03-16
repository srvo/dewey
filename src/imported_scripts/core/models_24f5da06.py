from django.db import models
from django.utils import timezone


class Contact(models.Model):
    email = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    domain = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Additional fields for enhanced contact management
    last_contacted = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags

    RELATIONSHIP_CHOICES = [
        ("subscriber", "Email Subscriber"),
        ("client", "Active Client"),
        ("lead", "Potential Client"),
        ("former", "Former Client"),
        ("none", "No Relationship"),
    ]

    relationship_status = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        default="none",
        help_text="Current relationship with the contact",
    )

    class Meta:
        ordering = ["name", "email"]

    def __str__(self) -> str:
        return f"{self.name or 'Unknown'} <{self.email}>"
