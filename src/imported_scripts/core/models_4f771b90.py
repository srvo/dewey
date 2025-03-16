"""Database models for the application.

This module defines the core database models using Django's ORM. It includes models for:
- Tags and contact tagging
- Email processing and tracking
- Contact management and enrichment
- Event logging and history
- Background task management

The models follow these design principles:
1. UUID primary keys for all models
2. Soft delete support via deleted_at timestamps
3. Version tracking for optimistic locking
4. JSON fields for flexible metadata storage
5. Comprehensive audit trails
6. Relationship tracking through association tables

Key Features:
- Tagging system with metadata
- Email processing pipeline tracking
- Contact enrichment workflow
- Event logging for system operations
- Background task management with retries
- Soft delete implementation
- Versioned history tracking

Implementation Details:
- All models use UUID primary keys for better security and distributed systems support
- Soft delete implemented through deleted_at timestamp fields
- Version tracking helps prevent concurrent modification conflicts
- JSON fields provide flexibility for evolving data structures
- Comprehensive indexes optimize common query patterns
- Many-to-many relationships use through models for additional metadata
- Model methods encapsulate business logic and validation
- Clean methods ensure data consistency
- Save methods handle version increments and automatic field updates
"""

import hashlib
import json
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Tag(models.Model):
    """Tags for categorizing contacts with metadata and color coding.

    Attributes:
    ----------
        id (UUIDField): Primary key using UUID for better security and distributed systems support
        name (CharField): Unique name of the tag (max 100 chars)
        description (TextField): Optional description of the tag's purpose
        color (CharField): Hex color code for UI display (default: #808080 gray)
        created_at (DateTimeField): Timestamp when tag was created (auto-set)
        updated_at (DateTimeField): Timestamp when tag was last updated (auto-update)

    Methods:
    -------
        __str__: Returns the tag name for display purposes

    Meta:
        verbose_name: Singular name for admin interface
        verbose_name_plural: Plural name for admin interface
        ordering: Default ordering by name
        indexes: Database indexes for optimized queries

    Example:
    -------
        >>> tag = Tag(name="VIP", description="Important contacts", color="#FF0000")
        >>> tag.save()
        >>> str(tag)
        'VIP'

    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    color = models.CharField(max_length=7, default="#808080")  # Hex color code
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="tag_name_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of tag.

        Returns:
        -------
            str: The name of the tag

        Example:
        -------
            >>> tag = Tag(name="VIP")
            >>> str(tag)
            'VIP'

        """
        return self.name


class ContactTag(models.Model):
    """Association between contacts and tags with additional metadata.

    This through-model enables many-to-many relationships between contacts and tags
    while storing additional metadata about each association.

    Attributes:
    ----------
        id (UUIDField): Primary key using UUID
        contact (ForeignKey): Reference to associated Contact
        tag (ForeignKey): Reference to associated Tag
        added_by (CharField): User/system that created the association
        notes (TextField): Optional notes about the association
        created_at (DateTimeField): Timestamp when association was created
        updated_at (DateTimeField): Timestamp when association was last updated

    Methods:
    -------
        __str__: Returns a string representation of the association

    Meta:
        verbose_name: Singular name for admin interface
        verbose_name_plural: Plural name for admin interface
        unique_together: Ensures unique contact-tag pairs
        indexes: Database indexes for optimized queries

    Example:
    -------
        >>> contact = Contact.objects.get(id=1)
        >>> tag = Tag.objects.get(id=1)
        >>> association = ContactTag(contact=contact, tag=tag, added_by="admin")
        >>> association.save()
        >>> str(association)
        'John Doe - VIP'

    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(
        "Contact",
        on_delete=models.CASCADE,
        related_name="tag_associations",
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="contact_associations",
    )
    added_by = models.CharField(max_length=255, default="system")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contact Tag"
        verbose_name_plural = "Contact Tags"
        unique_together = ("contact", "tag")
        indexes = [
            models.Index(fields=["contact", "tag"], name="contact_tag_idx"),
            models.Index(fields=["created_at"], name="contact_tag_created_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of contact tag.

        Returns:
        -------
            str: String in format "Contact Name - Tag Name"

        Example:
        -------
            >>> association = ContactTag(contact__name="John Doe", tag__name="VIP")
            >>> str(association)
            'John Doe - VIP'

        """
        return f"{self.contact.name} - {self.tag.name}"


class Config(models.Model):
    """Configuration key-value store."""

    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
        indexes = [
            models.Index(fields=["key"], name="config_key_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of config."""
        return f"{self.key}: {self.value}"


class EmailLabelHistory(models.Model):
    """History of email label changes."""

    ACTIONS = [
        ("ADDED", "Added"),
        ("REMOVED", "Removed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.ForeignKey(
        "Email",
        on_delete=models.CASCADE,
        related_name="label_history",
    )
    label_id = models.CharField(max_length=255)
    action = models.CharField(max_length=10, choices=ACTIONS)
    changed_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Email Label History"
        verbose_name_plural = "Email Label Histories"
        indexes = [
            models.Index(fields=["email", "label_id"], name="email_label_idx"),
            models.Index(fields=["created_at"], name="label_history_created_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of label history."""
        return f"{self.email.subject} - {self.label_id} {self.action}"


class Message(models.Model):
    """Message model for storing individual messages."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.TextField()
    body = models.TextField()
    sender = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        indexes = [
            models.Index(fields=["sender"], name="message_sender_idx"),
            models.Index(fields=["created_at"], name="message_created_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of message."""
        return f"{self.subject} from {self.sender}"


class Thread(models.Model):
    """Thread model for grouping related messages."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Thread"
        verbose_name_plural = "Threads"
        indexes = [
            models.Index(fields=["created_at"], name="thread_created_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of thread."""
        return self.subject


class MessageThreadAssociation(models.Model):
    """Association between messages and threads."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="thread_associations",
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="message_associations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Message Thread Association"
        verbose_name_plural = "Message Thread Associations"
        unique_together = ("message", "thread")
        indexes = [
            models.Index(fields=["message", "thread"], name="message_thread_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of association."""
        return f"{self.message.subject} in {self.thread.subject}"


class Contact(models.Model):
    """Contact model for storing email contact information."""

    PRONOUN_CHOICES = [
        ("he/him", "he/him"),
        ("she/her", "she/her"),
        ("they/them", "they/them"),
        ("other", "other"),
        ("unspecified", "unspecified"),
    ]

    ENRICHMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.IntegerField(default=1, help_text="Optimistic locking version")

    # Basic Information
    first_name = models.CharField(max_length=100, default="", blank=True)
    last_name = models.CharField(max_length=100, default="", blank=True)
    pronouns = models.CharField(
        max_length=20,
        choices=PRONOUN_CHOICES,
        default="unspecified",
        blank=True,
    )
    custom_pronouns = models.CharField(max_length=50, blank=True, default="")

    # Email Information
    primary_email = models.EmailField(unique=True)
    additional_emails = models.JSONField(default=list, blank=True)
    domain = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Email domain for categorization",
    )

    # Interaction Metrics
    interaction_count = models.IntegerField(default=0)
    last_interaction = models.DateTimeField(null=True, blank=True)
    avg_priority = models.FloatField(default=0.0, help_text="Calculated priority score")
    relationship_score = models.FloatField(
        default=0.0,
        help_text="Overall relationship strength",
    )
    last_priority_change = models.DateTimeField(null=True, blank=True)

    # Enrichment Information
    enrichment_status = models.CharField(
        max_length=20,
        choices=ENRICHMENT_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    last_enriched = models.DateTimeField(null=True, blank=True)
    enrichment_source = models.CharField(max_length=100, blank=True)
    confidence_score = models.FloatField(
        default=0.0,
        help_text="Data quality confidence (0.0-1.0)",
    )

    # Additional Data
    contact_metadata = models.JSONField(default=dict, blank=True)
    tags = models.ManyToManyField(Tag, through=ContactTag, related_name="contacts")

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["primary_email"], name="contact_primary_email_idx"),
            models.Index(fields=["last_name", "first_name"], name="contact_name_idx"),
            models.Index(fields=["domain"], name="contact_domain_idx"),
            models.Index(fields=["enrichment_status"], name="contact_enrichment_idx"),
            models.Index(
                fields=["relationship_score"],
                name="contact_relationship_idx",
            ),
        ]

    def __str__(self) -> str:
        """Return string representation of contact."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return f"{full_name or '(No name)'} <{self.primary_email}>"

    def add_tag(self, tag_name, added_by="system", notes="") -> None:
        """Add a tag to the contact."""
        tag, _ = Tag.objects.get_or_create(name=tag_name)
        ContactTag.objects.get_or_create(
            contact=self,
            tag=tag,
            defaults={
                "added_by": added_by,
                "notes": notes,
            },
        )

    def remove_tag(self, tag_name) -> None:
        """Remove a tag from the contact."""
        try:
            tag = Tag.objects.get(name=tag_name)
            ContactTag.objects.filter(contact=self, tag=tag).delete()
        except Tag.DoesNotExist:
            pass

    def get_tags_with_metadata(self):
        """Get all tags with their metadata."""
        return self.tag_associations.select_related("tag").all()

    def update_enrichment_status(self, status, source=None) -> None:
        """Update enrichment status and related fields."""
        self.enrichment_status = status
        self.last_enriched = timezone.now()
        if source:
            self.enrichment_source = source
        self.save(
            update_fields=["enrichment_status", "last_enriched", "enrichment_source"],
        )

    def update_relationship_score(self, score) -> None:
        """Update relationship score and record change time."""
        self.relationship_score = score
        self.last_priority_change = timezone.now()
        self.save(update_fields=["relationship_score", "last_priority_change"])

    def soft_delete(self, deleted_by) -> None:
        """Soft delete the contact."""
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=["deleted_at", "deleted_by"])

    def clean(self) -> None:
        """Validate the model."""
        super().clean()
        # Ensure additional_emails doesn't contain primary_email
        if self.primary_email in self.additional_emails:
            self.additional_emails.remove(self.primary_email)
        # Ensure custom_pronouns is only set when pronouns is "other"
        if self.pronouns != "other":
            self.custom_pronouns = ""
        # Extract and store domain from primary email
        if self.primary_email:
            self.domain = self.primary_email.split("@")[-1]

    def save(self, *args, **kwargs) -> None:
        """Save the model."""
        self.clean()
        # Increment version on each save
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)


class ContactHistory(models.Model):
    """Audit trail for contact changes.

    Implements full history tracking for Contact model changes using
    a versioned history pattern. Stores both the changed fields and
    their previous/new values.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="history_records",
    )
    version = models.IntegerField(help_text="Change version number")
    changed_fields = models.JSONField(help_text="List of changed field names")
    previous_values = models.JSONField(help_text="Values before change")
    new_values = models.JSONField(help_text="Values after change")
    change_type = models.CharField(
        max_length=20,
        choices=[
            ("create", "Create"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("restore", "Restore"),
        ],
    )
    change_reason = models.TextField(blank=True, help_text="Reason for the change")
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context",
    )
    created_by = models.CharField(max_length=255, help_text="User/system making change")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contact History"
        verbose_name_plural = "Contact Histories"
        ordering = ["-created_at", "-version"]
        indexes = [
            models.Index(
                fields=["contact", "version"],
                name="contact_history_version_idx",
            ),
            models.Index(
                fields=["contact", "created_at"],
                name="contact_history_date_idx",
            ),
            models.Index(fields=["change_type"], name="contact_history_type_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of history record."""
        return f"{self.contact.name} - {self.change_type} (v{self.version})"


class Email(models.Model):
    """Email model for storing processed email information."""

    STATUS_CHOICES = [
        ("new", "New"),
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("ignored", "Ignored"),
    ]

    IMPORTANCE_CHOICES = [
        (0, "Low"),
        (1, "Normal"),
        (2, "High"),
        (3, "Urgent"),
    ]

    CATEGORY_CHOICES = [
        ("inbox", "Inbox"),
        ("sent", "Sent"),
        ("draft", "Draft"),
        ("spam", "Spam"),
        ("trash", "Trash"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.IntegerField(default=1, help_text="Processing version")

    # Gmail Information
    gmail_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255, blank=True, null=True)
    history_id = models.CharField(max_length=255, blank=True, null=True)

    # Email Content
    subject = models.TextField(blank=True, null=True)
    snippet = models.TextField(blank=True, help_text="Email preview text")
    from_email = models.TextField()
    from_name = models.TextField(blank=True, help_text="Sender name")
    to_emails = models.JSONField(default=list)
    cc_emails = models.JSONField(default=list, blank=True)
    bcc_emails = models.JSONField(default=list, blank=True)
    raw_content = models.TextField(blank=True, null=True)
    plain_body = models.TextField(blank=True, null=True, help_text="Plain text content")
    html_body = models.TextField(blank=True, null=True, help_text="HTML content")

    # Email Metadata
    received_at = models.DateTimeField()
    size_estimate = models.IntegerField(default=0, help_text="Size in bytes")
    labels = models.JSONField(default=list, blank=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="inbox",
        db_index=True,
    )
    importance = models.IntegerField(
        choices=IMPORTANCE_CHOICES,
        default=1,
        db_index=True,
    )

    # Processing Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        db_index=True,
    )
    processed = models.BooleanField(default=False)
    processing_version = models.IntegerField(default=1)
    processed_date = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Flags
    is_draft = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_trashed = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Additional Data
    email_metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"
        indexes = [
            models.Index(fields=["gmail_id"], name="email_gmail_idx"),
            models.Index(fields=["thread_id"], name="email_thread_idx"),
            models.Index(fields=["history_id"], name="email_history_idx"),
            models.Index(fields=["received_at"], name="email_received_idx"),
            models.Index(fields=["status", "processed"], name="email_status_idx"),
            models.Index(fields=["category", "importance"], name="email_category_idx"),
            models.Index(fields=["from_email"], name="email_sender_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of email."""
        return f"{self.subject or '(No subject)'} ({self.gmail_id})"

    def update_status(self, status, error=None) -> None:
        """Update email processing status."""
        self.status = status
        if status == "processed":
            self.processed = True
            self.processed_date = timezone.now()
        elif status == "failed" and error:
            self.error_message = str(error)
        self.save(
            update_fields=["status", "processed", "processed_date", "error_message"],
        )

    def increment_processing_version(self) -> None:
        """Increment the processing version."""
        self.processing_version += 1
        self.version += 1
        self.save(update_fields=["processing_version", "version"])

    def clean(self) -> None:
        """Validate model fields."""
        super().clean()

        # Validate to_emails is a list
        if not isinstance(self.to_emails, list):
            raise ValidationError({"to_emails": "to_emails must be a list"})

        # Validate from_email is required
        if not self.from_email:
            raise ValidationError({"from_email": "from_email is required"})

        # Validate received_at is required
        if not self.received_at:
            raise ValidationError({"received_at": "received_at is required"})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)


class RawEmail(models.Model):
    """Raw email data from Gmail API."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gmail_message_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255)
    history_id = models.CharField(max_length=255)
    raw_data = models.JSONField()
    checksum = models.CharField(max_length=64, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Raw Email"
        verbose_name_plural = "Raw Emails"
        indexes = [
            models.Index(fields=["gmail_message_id"], name="raw_email_gmail_idx"),
            models.Index(fields=["thread_id"], name="raw_email_thread_idx"),
            models.Index(fields=["history_id"], name="raw_email_history_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of raw email."""
        return f"Raw Email {self.gmail_message_id}"

    def save(self, *args, **kwargs) -> None:
        # Calculate checksum based on raw_data
        raw_json = json.dumps(self.raw_data, sort_keys=True).encode("utf-8")
        self.checksum = hashlib.sha256(raw_json).hexdigest()
        super().save(*args, **kwargs)


class EmailContactAssociation(models.Model):
    """Association between emails and contacts."""

    ASSOCIATION_TYPES = [
        ("from", "From"),
        ("to", "To"),
        ("cc", "CC"),
        ("bcc", "BCC"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="contact_associations",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="email_associations",
    )
    association_type = models.CharField(
        max_length=4,
        choices=ASSOCIATION_TYPES,
        default="to",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Contact Association"
        verbose_name_plural = "Email Contact Associations"
        unique_together = ("email", "contact", "association_type")
        indexes = [
            models.Index(
                fields=["email", "contact", "association_type"],
                name="email_contact_assoc_idx",
            ),
            models.Index(
                fields=["contact", "association_type"],
                name="contact_assoc_type_idx",
            ),
        ]

    def __str__(self) -> str:
        """Return string representation of association."""
        return f"{self.contact.email} {self.association_type} {self.email.subject or '(No subject)'}"


class EventLog(models.Model):
    """Event log for tracking system events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    performed_by = models.CharField(
        max_length=255,
        default="system",
        blank=True,
    )  # Added default and blank
    created_at = models.DateTimeField(auto_now_add=True)
    email = models.ForeignKey(Email, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Event Log"
        verbose_name_plural = "Event Logs"
        indexes = [
            models.Index(fields=["event_type"], name="event_type_idx"),
            models.Index(fields=["created_at"], name="event_created_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of event log."""
        return f"{self.event_type} at {self.created_at}"


class EnrichmentTask(models.Model):
    """Background task management for contact enrichment.

    Tracks enrichment tasks with retry logic and status monitoring.
    Supports multiple entity types and enrichment sources.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("skipped", "Skipped"),
    ]

    ENTITY_TYPE_CHOICES = [
        ("contact", "Contact"),
        ("email", "Email"),
        ("thread", "Thread"),
    ]

    TASK_TYPE_CHOICES = [
        ("contact_info", "Contact Information"),
        ("social_profiles", "Social Profiles"),
        ("company_info", "Company Information"),
        ("relationship_score", "Relationship Score"),
        ("email_analysis", "Email Analysis"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.UUIDField()
    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    version = models.IntegerField(default=1, help_text="Task version for retries")

    # Task Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    priority = models.IntegerField(
        default=0,
        help_text="Processing priority (higher = more urgent)",
    )
    attempts = models.IntegerField(default=0, help_text="Number of processing attempts")
    max_attempts = models.IntegerField(default=3, help_text="Maximum allowed attempts")

    # Timing
    last_attempt = models.DateTimeField(null=True, blank=True)
    next_attempt = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to process this task",
    )

    # Results
    result = models.JSONField(null=True, blank=True, help_text="Task result data")
    error_message = models.TextField(blank=True)
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional task context",
    )

    # Audit Fields
    created_by = models.CharField(max_length=255)
    updated_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Enrichment Task"
        verbose_name_plural = "Enrichment Tasks"
        ordering = ["-priority", "next_attempt", "created_at"]
        indexes = [
            models.Index(
                fields=["entity_type", "entity_id"],
                name="enrichment_entity_idx",
            ),
            models.Index(
                fields=["status", "next_attempt"],
                name="enrichment_status_idx",
            ),
            models.Index(fields=["task_type", "status"], name="enrichment_type_idx"),
            models.Index(fields=["priority", "status"], name="enrichment_priority_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of task."""
        return (
            f"{self.task_type} for {self.entity_type}:{self.entity_id} ({self.status})"
        )

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = "in_progress"
        self.attempts += 1
        self.last_attempt = timezone.now()
        self.save(update_fields=["status", "attempts", "last_attempt"])

    def mark_completed(self, result=None) -> None:
        """Mark task as completed with optional result."""
        self.status = "completed"
        if result:
            self.result = result
        self.save(update_fields=["status", "result"])

    def mark_failed(self, error, retry_after=None) -> None:
        """Mark task as failed with error and optional retry."""
        if self.attempts >= self.max_attempts:
            self.status = "failed"
        else:
            self.status = "pending"
            self.next_attempt = retry_after or (
                timezone.now() + timezone.timedelta(minutes=5 * (2**self.attempts))
            )
        self.error_message = str(error)
        self.save(update_fields=["status", "next_attempt", "error_message"])

    def cancel(self, reason=None) -> None:
        """Cancel the task."""
        self.status = "cancelled"
        if reason:
            self.error_message = reason
        self.save(update_fields=["status", "error_message"])


class AutomatedOperation:
    """Base class for automated operations that modify data in the database.

    This class provides standard methods for tracking operations via enrichment tasks.
    Any automated operation that modifies data should inherit from this class.
    """

    def __init__(self, entity_type: str, task_type: str) -> None:
        self.entity_type = entity_type
        self.task_type = task_type

    def create_enrichment_task(self, entity_id: int) -> "EnrichmentTask":
        """Create a new enrichment task for this operation."""
        return EnrichmentTask.objects.create(
            entity_type=self.entity_type,
            entity_id=entity_id,
            task_type=self.task_type,
            created_by="celery",
            updated_by="celery",
            status="in_progress",
        )

    def complete_task(self, task: "EnrichmentTask", result: dict) -> None:
        """Mark an enrichment task as completed with results."""
        task.mark_completed(result=result)

    def fail_task(self, task: "EnrichmentTask", error: str) -> None:
        """Mark an enrichment task as failed with error details."""
        task.mark_failed(error)
