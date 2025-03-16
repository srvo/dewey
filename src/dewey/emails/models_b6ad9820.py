# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

from django.db import models


class Email(models.Model):
    """Model for storing email messages.

    This model stores email messages synced from IMAP, including metadata
    and content. The raw email data is stored in the related RawEmail model.
    """

    # Message identifiers
    message_id = models.CharField(max_length=255, unique=True)

    # Headers
    subject = models.CharField(max_length=255, blank=True)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_emails = models.JSONField(default=list)  # List of email addresses
    cc_emails = models.JSONField(default=list, blank=True)
    bcc_emails = models.JSONField(default=list, blank=True)

    # Content
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)

    # Metadata
    received_at = models.DateTimeField()
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.subject or "(No subject)"

    class Meta:
        indexes = [
            models.Index(fields=["message_id"]),
            models.Index(fields=["from_email"]),
            models.Index(fields=["received_at"]),
        ]


class RawEmail(models.Model):
    """Model for storing raw email data.

    This model stores the raw email data in RFC822 format, along with
    metadata about when it was processed. This is useful for debugging
    and reprocessing emails if needed.
    """

    email = models.OneToOneField(
        Email,
        on_delete=models.CASCADE,
        related_name="raw_email",
    )
    raw_data = models.BinaryField()  # Store as bytes to preserve encoding
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Raw email for {self.email.subject}"

    class Meta:
        indexes = [
            models.Index(fields=["processed_at"]),
        ]
