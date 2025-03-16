"""Syzygy app configuration."""

from django.apps import AppConfig


class SyzygyConfig(AppConfig):
    """Configuration for Syzygy app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "syzygy"
    verbose_name = "Syzygy"

    def ready(self) -> None:
        """Initialize app configuration."""
        from django.contrib import admin

        admin.site.site_header = "Syzygy"
        admin.site.site_title = "Syzygy"
        admin.site.index_title = "Ethical CapitalResearch Management"
