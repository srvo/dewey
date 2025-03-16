"""Django application configuration for the database module.

This configuration class provides settings and initialization
for the database application, including:
- Default auto field configuration
- Application name registration
- Database connection management
- Model registration and migrations
- Any database-specific initialization logic

The configuration ensures proper integration with Django's ORM
and provides a consistent interface for database operations.
"""

from django.apps import AppConfig


class DatabaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "database"
    verbose_name = "Database Management"
