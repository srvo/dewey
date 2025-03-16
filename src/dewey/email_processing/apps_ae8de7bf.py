# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Email processing app configuration."""

from django.apps import AppConfig


class EmailProcessingConfig(AppConfig):
    """Configuration for the email processing app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "email_processing"

    def ready(self) -> None:
        """Import signal handlers when Django starts."""
        import email_processing.signals  # noqa
